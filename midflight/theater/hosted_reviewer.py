"""Hosted OpenAI reviews through the supported Codex CLI and its saved sign-in."""

import json
import os
import shutil
import signal
import subprocess
import tempfile
import time
from contextlib import suppress
from pathlib import Path

from midflight.ports import ReviewerUnavailable
from midflight.theater.review_policy import PeerReviewPolicy


def strict_schema(schema):
    schema = json.loads(json.dumps(schema))

    def visit(node):
        if isinstance(node, dict):
            if node.get("type") == "object":
                node["additionalProperties"] = False
                node["required"] = list(node.get("properties", {}))
            for value in node.values():
                visit(value)
        elif isinstance(node, list):
            for value in node:
                visit(value)

    visit(schema)
    return schema


def _run_cli(command, *, prompt, cwd, timeout):
    """Bound the whole CLI process group, including its native child process."""
    proc = subprocess.Popen(
        command,
        cwd=cwd,
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
        start_new_session=True,
    )
    try:
        proc.communicate(prompt, timeout=timeout)
        return proc.returncode
    finally:
        # The installed CLI can be a Node wrapper around a native executable.
        # Killing only the wrapper can leave inference running after a timeout.
        with suppress(ProcessLookupError):
            os.killpg(proc.pid, signal.SIGKILL)
        proc.wait(timeout=5)


class HostedReviewer(PeerReviewPolicy):
    # Reuse review policy and second checks; replace only the inference transport.
    def __init__(self, *, call_timeout=20, review_timeout=30):
        super().__init__("hosted-codex")
        self.call_timeout = call_timeout
        self.review_timeout = review_timeout
        self._deadline = None
        self._failure = None

    def review_claim(self, request):
        self._deadline = time.monotonic() + self.review_timeout
        self._failure = None
        try:
            result = super().review_claim(request)
            # The generic policy may downgrade an unchecked finding to info.
            # A transport timeout in this hosted adapter must instead stay pending.
            if self._failure is not None:
                raise self._failure
            return result
        finally:
            self._deadline = None

    def _call(self, system, task, data, tool, schema):
        executable = shutil.which("codex")
        if not executable:
            raise ReviewerUnavailable("Hosted reviewer: Codex CLI is not installed.")
        prompt = (
            "You are a bounded coordination reviewer. Use only the supplied data. "
            "Do not run tools, read files, or contact services. Return only the requested JSON.\n\n"
            + system
            + "\n\n"
            + task
            + "\nReturn the answer as a JSON object matching the output schema, "
            "instead of calling a tool.\n<data>\n" + json.dumps(data, indent=1) + "\n</data>"
        )
        try:
            with tempfile.TemporaryDirectory(prefix="midflight-review-") as folder:
                root = Path(folder)
                schema_path = root / "schema.json"
                answer_path = root / "answer.json"
                schema_path.write_text(json.dumps(strict_schema(schema)))
                timeout = self.call_timeout
                if self._deadline is not None:
                    timeout = min(timeout, self._deadline - time.monotonic())
                if timeout <= 0:
                    raise ReviewerUnavailable("Hosted reviewer: review time budget exhausted.")
                returncode = _run_cli(
                    [
                        executable,
                        "exec",
                        "--ignore-user-config",
                        "--ephemeral",
                        "--sandbox",
                        "read-only",
                        "--skip-git-repo-check",
                        "--output-schema",
                        str(schema_path),
                        "--output-last-message",
                        str(answer_path),
                        "--color",
                        "never",
                        "-c",
                        'model_reasoning_effort="low"',
                        "-c",
                        "features.shell_tool=false",
                        "-",
                    ],
                    prompt=prompt,
                    cwd=root,
                    timeout=timeout,
                )
                if returncode != 0:
                    # The CLI manages credentials; do not expose its stderr or tokens in findings.
                    raise ReviewerUnavailable(
                        f"Hosted reviewer: Codex exited with code {returncode}. "
                        "Check codex login status and account availability."
                    )
                answer = json.loads(answer_path.read_text())
                if not isinstance(answer, dict):
                    raise ValueError("The hosted model returned a non-object response.")
                return answer
        except ReviewerUnavailable as error:
            self._failure = error
            raise
        except (OSError, ValueError, subprocess.TimeoutExpired) as error:
            failure = ReviewerUnavailable(f"Hosted reviewer: {type(error).__name__}")
            self._failure = failure
            raise failure from error
