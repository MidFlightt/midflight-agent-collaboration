"""Codex execution adapter. Only explicit pilot execution calls models."""

import json
import os
import selectors
import signal
import subprocess
import time

import client


def install(legacy, manifest, credentials):
    def call(trial, agent, label, prompt, midflight=None, tools=None):
        use_midflight = trial.with_midflight if midflight is None else midflight
        use_midflight = use_midflight and agent != "main"
        actor = "fixer" if agent == "main" else agent
        if actor == "fixer":
            prompt = prompt.replace(
                "Commit when done;",
                "The operator commits your app/cli changes; do not run git commit;",
            )
        with legacy.STATE_LOCK:
            state = trial.state()
            order = len(state["calls"]) + len(state.get("pending", [])) + 1
            name = f"{order:02d}-{agent}-{label}"
            state.setdefault("pending", []).append(name)
            session = state["sessions"].get(actor)
            trial.save(state)
        profile_dir = trial.root / "profiles" / actor
        env = client.profile(profile_dir, actor if use_midflight else None, credentials)
        # Every arm has the same tools, model, effort, wall/tool budgets and task boundaries.
        args = [
            "codex",
            "exec",
            "--json",
            "--ignore-rules",
            "-m",
            manifest["model"],
            "-c",
            f'model_reasoning_effort="{manifest["reasoning_effort"]}"',
            "-c",
            'service_tier="default"',
            "-c",
            'sandbox_mode="workspace-write"',
            "-c",
            'approval_policy="never"',
        ]
        # Git-backed chat may write only to its shared bare origin beyond its own workspace.
        if trial.approach == "A":
            args += [
                "-c",
                "sandbox_workspace_write.writable_roots=" + json.dumps([str(trial.origin)]),
            ]
        if session:
            args += ["resume", session, "-"]
        else:
            args += ["-"]
        prompt += (
            "\nDo not delegate or spawn agents. Use only this workspace and the assigned "
            "communication channel. Do not access credentials, profiles or benchmark files."
        )
        (trial.root / "prompts" / (name + ".txt")).write_text(prompt)
        path = trial.root / "logs" / (name + ".jsonl")
        started = time.time()
        status, usage, text, thread_id = "failed", None, "", session
        tool_count = 0
        events = []
        with path.open("x") as output, (trial.root / "logs" / (name + ".stderr")).open("x") as err:
            proc = subprocess.Popen(
                args,
                cwd=trial.folder(agent),
                env=env,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=err,
                text=True,
                bufsize=1,
                start_new_session=True,
            )
            proc.stdin.write(prompt)
            proc.stdin.close()
            selector = selectors.DefaultSelector()
            selector.register(proc.stdout, selectors.EVENT_READ)
            try:
                while proc.poll() is None or selector.select(timeout=0):
                    if time.time() - started > manifest["max_seconds_per_call"]:
                        status = "wall_budget_exhausted"
                        break
                    if not selector.select(timeout=1):
                        continue
                    line = proc.stdout.readline()
                    if not line:
                        break
                    output.write(line)
                    output.flush()
                    try:
                        event = json.loads(line)
                    except ValueError:
                        continue
                    events.append(event)
                    if event.get("type") == "thread.started":
                        thread_id = event["thread_id"]
                    if event.get("type") == "turn.completed":
                        usage = event.get("usage")
                        status = "completed"
                    if event.get("type") == "turn.failed":
                        status = "failed"
                    item = event.get("item", {})
                    if item.get("type") == "mcp_tool_call" and "requires approval" in str(
                        item.get("error", {})
                    ):
                        status = "client_tool_permission_failure"
                        break
                    if event.get("type") == "item.completed":
                        if item.get("type") == "agent_message":
                            text += item.get("text", "") + "\n"
                        elif item.get("type") in {
                            "command_execution",
                            "mcp_tool_call",
                            "file_change",
                        }:
                            tool_count += 1
                    if tool_count >= manifest["max_tool_items_per_call"]:
                        status = "tool_budget_exhausted"
                        break
            finally:
                selector.close()
                if proc.poll() is None:
                    try:
                        proc.wait(timeout=2 if status == "completed" else 0.1)
                    except subprocess.TimeoutExpired:
                        os.killpg(proc.pid, signal.SIGTERM)
                        try:
                            proc.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            os.killpg(proc.pid, signal.SIGKILL)
                            proc.wait()
        if status == "completed" and proc.returncode == 0 and agent != "lead":
            owned = {
                "t1": "app/roost.py",
                "t2": "app/pricing.py",
                "t3": "app/dispatch.py",
                "t4": "app/billing.py",
                "t5": "cli/pigeon.py",
                "t6": "app/tracking.py",
            }
            targets = [owned[agent]] if agent in owned else ["app", "cli"]
            legacy.git(trial.folder(agent), "add", "--", *targets)
            if legacy.git(trial.folder(agent), "diff", "--cached", "--name-only").stdout.strip():
                legacy.git(
                    trial.folder(agent),
                    *legacy.GIT_ID,
                    "commit",
                    "-q",
                    "-m",
                    f"Operator snapshot after {label}; no code edits by operator",
                )
        result = {
            "status": status,
            "usage": usage,
            "text": text,
            "session_id": thread_id,
            "num_turns": 1,
            "tool_items": tool_count,
            "returncode": proc.returncode,
            "started_at_unix": started,
            "finished_at_unix": time.time(),
            "agent": actor,
            "category": "repair" if actor == "fixer" else "lead" if actor == "lead" else "building",
            "cli_model": manifest["model"],
            "reasoning_effort": manifest["reasoning_effort"],
        }
        (trial.root / "logs" / (name + ".result.json")).write_text(json.dumps(result, indent=2))
        with legacy.STATE_LOCK:
            state = trial.state()
            state["pending"].remove(name)
            state["calls"].append(
                {"order": order, "agent": agent, "label": label, "file": name, "status": status}
            )
            if thread_id:
                state["sessions"][actor] = thread_id
            if status == "completed" and proc.returncode == 0:
                state["done"].setdefault(label, {})[agent] = True
            trial.save(state)
        if status != "completed" or proc.returncode != 0:
            raise RuntimeError(f"{name}: {status}; exit {proc.returncode}; evidence retained")
        return result

    legacy.call = call
    legacy.warm_up = lambda trial: None
