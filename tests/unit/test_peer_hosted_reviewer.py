import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from midflight.ports import ReviewerUnavailable
from midflight.theater.hosted_reviewer import HostedReviewer, strict_schema


class HostedReviewerTest(unittest.TestCase):
    def test_schema_closes_nested_objects_and_requires_their_fields(self):
        source = {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {"answer": {"type": "string"}},
                    },
                }
            },
        }
        result = strict_schema(source)
        self.assertFalse(result["additionalProperties"])
        nested = result["properties"]["items"]["items"]
        self.assertEqual(nested["required"], ["answer"])
        self.assertFalse(nested["additionalProperties"])
        self.assertNotIn("additionalProperties", source)

    def test_uses_supported_cli_auth_and_structured_output(self):
        def respond(command, **kwargs):
            Path(command[command.index("--output-last-message") + 1]).write_text('{"findings": []}')
            self.assertIn("--ignore-user-config", command)
            self.assertIn("--ephemeral", command)
            self.assertEqual(command[command.index("--sandbox") + 1], "read-only")
            self.assertIn("<data>", kwargs["input"])
            return subprocess.CompletedProcess(command, 0, "", "")

        with (
            patch("midflight.theater.hosted_reviewer.shutil.which", return_value="/path/codex"),
            patch("midflight.theater.hosted_reviewer.subprocess.run", side_effect=respond),
        ):
            self.assertEqual(
                HostedReviewer()._call("policy", "review", {}, "findings", {"type": "object"}),
                {"findings": []},
            )

    def test_failure_and_timeout_never_return_approval_or_cli_secrets(self):
        failure = subprocess.CompletedProcess([], 1, "", "private CLI diagnostics")
        with (
            patch("midflight.theater.hosted_reviewer.shutil.which", return_value="/path/codex"),
            patch("midflight.theater.hosted_reviewer.subprocess.run", return_value=failure),
        ):
            with self.assertRaises(ReviewerUnavailable) as caught:
                HostedReviewer()._call("", "", {}, "", {})
            self.assertNotIn("private CLI diagnostics", str(caught.exception))
        with (
            patch("midflight.theater.hosted_reviewer.shutil.which", return_value="/path/codex"),
            patch(
                "midflight.theater.hosted_reviewer.subprocess.run",
                side_effect=subprocess.TimeoutExpired("codex", 90),
            ),
            self.assertRaises(ReviewerUnavailable),
        ):
            HostedReviewer()._call("", "", {}, "", {})


if __name__ == "__main__":
    unittest.main()
