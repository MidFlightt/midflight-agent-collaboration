"""Hosted OpenAI reviews through the supported Codex CLI and its saved sign-in."""

import json
import shutil
import subprocess
import tempfile
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


class HostedReviewer(PeerReviewPolicy):
    # Reuse review policy and second checks; replace only the inference transport.
    def __init__(self):
        super().__init__("hosted-codex")

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
                result = subprocess.run(
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
                    input=prompt,
                    cwd=root,
                    capture_output=True,
                    text=True,
                    timeout=90,
                )
                if result.returncode != 0:
                    # The CLI manages credentials; do not expose its stderr or tokens in findings.
                    raise ReviewerUnavailable(
                        f"Hosted reviewer: Codex exited with code {result.returncode}. "
                        "Check codex login status and account availability."
                    )
                answer = json.loads(answer_path.read_text())
                if not isinstance(answer, dict):
                    raise ValueError("The hosted model returned a non-object response.")
                return answer
        except (OSError, ValueError, subprocess.TimeoutExpired) as error:
            raise ReviewerUnavailable(f"Hosted reviewer: {type(error).__name__}") from error
