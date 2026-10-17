"""The AI reviewer on Claude, through the Claude Code CLI, for trials on this machine.

Midflight's reviewer runs on Amazon Bedrock (`midflight.adapters.bedrock`). A laptop
without AWS credentials can still run a trial with a real model reviewer: this keeps
every prompt, schema, and second look of `BedrockReviewer` and only replaces the one
model call with `claude -p --json-schema`. It is a benchmark tool, not a product adapter:
results from it say "reviewer: Claude <model> via the CLI", not Nova.

    MIDFLIGHT_LOCAL_REVIEWER=claude python experiment/local_midflight.py serve

The model is `MIDFLIGHT_LOCAL_REVIEWER_MODEL` (default `haiku`: a small, fast model, as
Nova 2 Lite is on AWS).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import threading
from typing import Any

from midflight.adapters.bedrock import BedrockReviewer
from midflight.ports import ReviewerUnavailable

TIMEOUT = 90


class ClaudeReviewer(BedrockReviewer):
    def __init__(self, model: str | None = None) -> None:
        super().__init__(
            model_id=model or os.environ.get("MIDFLIGHT_LOCAL_REVIEWER_MODEL", "haiku")
        )
        self.calls = 0
        self.cost = 0.0
        self.seconds = 0.0
        self._lock = threading.Lock()
        # An empty folder, so the CLI loads no project instructions or settings.
        self._cwd = tempfile.mkdtemp(prefix="midflight-reviewer-")

    def _call(
        self, system: str, task: str, data: dict[str, Any], tool: str, schema: dict[str, Any]
    ) -> Any:
        message = f"{task}\n\n<data>\n{json.dumps(data, indent=1)}\n</data>"
        args = [
            shutil.which("claude") or "claude", "-p", "--model", self.model_id,
            "--output-format", "json", "--json-schema", json.dumps(schema),
            "--system-prompt", system, "--tools", "", "--strict-mcp-config",
            "--max-turns", "3",
            # Thinking off: a reviewer answer in about 5 s instead of 10 to 20.
            "--settings", json.dumps({"alwaysThinkingEnabled": False}),
        ]  # fmt: skip
        try:
            done = subprocess.run(
                args, input=message, capture_output=True, text=True, timeout=TIMEOUT,
                cwd=self._cwd,
            )  # fmt: skip
            reply = json.loads(done.stdout)
        except (subprocess.TimeoutExpired, ValueError) as error:
            raise ReviewerUnavailable(f"Claude CLI: {type(error).__name__}") from error
        with self._lock:
            self.calls += 1
            self.cost += float(reply.get("total_cost_usd") or 0)
            self.seconds += float(reply.get("duration_ms") or 0) / 1000
        answer = reply.get("structured_output")
        if reply.get("is_error") or not isinstance(answer, dict):
            raise ReviewerUnavailable("Claude CLI: no structured answer")
        return answer

    def stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "model": self.model_id,
                "calls": self.calls,
                "cost_usd": round(self.cost, 4),
                "seconds": round(self.seconds, 1),
            }
