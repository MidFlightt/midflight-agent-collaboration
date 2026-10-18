"""Isolated Codex profiles and model-free discovery for the pilot runner."""

import json
import os
import selectors
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODEL = "gpt-6.1-sol"
EFFORT = "medium"
URL = "https://127.0.0.1:19483"


def profile(path, agent=None, credentials=None):
    path.mkdir(parents=True, mode=0o700, exist_ok=True)
    auth = path / "auth.json"
    if not auth.exists():
        auth.symlink_to(Path.home() / ".codex/auth.json")
    config = (
        f'model = "{MODEL}"\nmodel_reasoning_effort = "{EFFORT}"\n'
        'approval_policy = "never"\nsandbox_mode = "workspace-write"\n'
        'project_doc_max_bytes = 0\nweb_search = "disabled"\n'
        "[features]\nmulti_agent = false\nmemories = false\n"
        "[sandbox_workspace_write]\nnetwork_access = true\n"
    )
    if agent is not None:
        token = credentials / (agent + ".token")
        if not token.is_file():
            raise ValueError(f"Missing private credential for {agent}")
        config += (
            "[mcp_servers.midflight-live]\ncommand = "
            + json.dumps(str(ROOT / ".venv/bin/python"))
            + '\nargs = ["-m", "experiment.communication.bridge"]\n'
            + "[mcp_servers.midflight-live.env]\nPYTHONPATH = "
            + json.dumps(str(ROOT))
            + '\nPIGEONPOST_RESPONSE_FORMAT = "compact-v1"\nMIDFLIGHT_URL = '
            + json.dumps(URL)
            + "\nMIDFLIGHT_TOKEN_FILE = "
            + json.dumps(str(token))
            + "\n"
            + "SSL_CERT_FILE = "
            + json.dumps(str(ROOT / "runs/local-backend/cert.pem"))
            + "\n"
            + "PIGEONPOST_TRACE = "
            + json.dumps(str(path / "bridge.jsonl"))
            + "\n"
        )
        for tool in ("join", "send", "check_in", "object"):
            config += f'\n[mcp_servers.midflight-live.tools.{tool}]\napproval_mode = "approve"\n'
    (path / "config.toml").write_text(config)
    return dict(os.environ, CODEX_HOME=str(path))


def discover(path, credentials):
    env = profile(path, "t1", credentials)
    with (path / "discovery-stderr.log").open("w") as err:
        proc = subprocess.Popen(
            ["codex", "app-server", "--stdio"],
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=err,
            text=True,
            bufsize=1,
        )
        selector = selectors.DefaultSelector()
        selector.register(proc.stdout, selectors.EVENT_READ)

        def rpc(identifier, method, params):
            proc.stdin.write(
                json.dumps({"id": identifier, "method": method, "params": params}) + "\n"
            )
            proc.stdin.flush()
            deadline = time.monotonic() + 45
            while time.monotonic() < deadline:
                if not selector.select(timeout=1):
                    continue
                line = proc.stdout.readline()
                if not line:
                    raise RuntimeError("Codex app-server exited")
                event = json.loads(line)
                if event.get("id") == identifier:
                    if "error" in event:
                        raise RuntimeError(event["error"])
                    return event["result"]
            raise TimeoutError(method)

        try:
            rpc(
                1,
                "initialize",
                {
                    "clientInfo": {"name": "pigeonpost-preflight", "version": "2"},
                    "capabilities": {"experimentalApi": True},
                },
            )
            proc.stdin.write('{"method":"initialized"}\n')
            proc.stdin.flush()
            models = rpc(2, "model/list", {})
            tools = rpc(3, "mcpServerStatus/list", {"serverName": "midflight-live"})
            thread = rpc(
                4, "thread/start", {"cwd": str(path), "model": MODEL, "approvalPolicy": "never"}
            )
            thread_id = thread["thread"]["id"]
            probes = {
                "join": {
                    "name": "operator-wrong-identity",
                    "task": "preflight",
                    "request_id": "preflight-denied",
                },
                "check_in": {"session_id": "operator-nonexistent-session"},
                "send": {
                    "session_id": "operator-nonexistent-session",
                    "kind": "message",
                    "body": "operator fixture rejected before mutation",
                    "to": ["t1"],
                    "request_id": "preflight-denied",
                },
                "object": {
                    "session_id": "operator-nonexistent-session",
                    "publication_id": 1,
                    "revision": 1,
                    "problem": "operator fixture",
                    "affects": "none",
                    "request_id": "preflight-denied",
                },
            }
            calls = {}
            for index, (tool, arguments) in enumerate(probes.items(), 5):
                calls[tool] = rpc(
                    index,
                    "mcpServer/tool/call",
                    {
                        "threadId": thread_id,
                        "server": "midflight-live",
                        "tool": tool,
                        "arguments": arguments,
                    },
                )
            result = {
                "cli_version": subprocess.check_output(["codex", "--version"], text=True).strip(),
                "model": MODEL,
                "reasoning_effort": EFFORT,
                "models": models,
                "mcp": tools,
                "model_calls": 0,
                "backend_tool_calls": 4,
                "rejection_probes": calls,
            }
            (path / "discovery.json").write_text(json.dumps(result, indent=2))
            return result
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
            selector.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--credentials", type=Path, required=True)
    args = parser.parse_args()
    result = discover(args.output.resolve(), args.credentials.resolve())
    print(
        json.dumps(
            {"cli_version": result["cli_version"], "model": MODEL, "mcp": result["mcp"]}, indent=2
        )
    )
