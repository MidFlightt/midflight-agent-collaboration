import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

import pytest

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
            self.assertIn("<data>", kwargs["prompt"])
            return 0

        with (
            patch("midflight.theater.hosted_reviewer.shutil.which", return_value="/path/codex"),
            patch("midflight.theater.hosted_reviewer._run_cli", side_effect=respond),
        ):
            self.assertEqual(
                HostedReviewer()._call("policy", "review", {}, "findings", {"type": "object"}),
                {"findings": []},
            )

    def test_failure_and_timeout_never_return_approval_or_cli_secrets(self):
        failure = 1
        with (
            patch("midflight.theater.hosted_reviewer.shutil.which", return_value="/path/codex"),
            patch("midflight.theater.hosted_reviewer._run_cli", return_value=failure),
        ):
            with self.assertRaises(ReviewerUnavailable) as caught:
                HostedReviewer()._call("", "", {}, "", {})
            self.assertNotIn("private CLI diagnostics", str(caught.exception))
        with (
            patch("midflight.theater.hosted_reviewer.shutil.which", return_value="/path/codex"),
            patch(
                "midflight.theater.hosted_reviewer._run_cli",
                side_effect=subprocess.TimeoutExpired("codex", 90),
            ),
            self.assertRaises(ReviewerUnavailable),
        ):
            HostedReviewer()._call("", "", {}, "", {})


if __name__ == "__main__":
    unittest.main()


def test_review_budget_is_shared_across_calls_and_timeout_cannot_approve():
    from midflight.theater.review_policy import PeerReviewPolicy

    reviewer = HostedReviewer(call_timeout=20, review_timeout=30)
    timeouts = []

    def run(command, **kwargs):
        timeouts.append(kwargs["timeout"])
        if len(timeouts) == 1:
            raise subprocess.TimeoutExpired(command, kwargs["timeout"])
        raise AssertionError("Unexpected extra model call")

    def review(self, request):
        # Emulate the generic second-check fallback: it swallows transport errors.
        try:
            self._call("policy", "confirm", {}, "confirm_conflict", {"type": "object"})
        except ReviewerUnavailable:
            return {"findings": []}

    with (
        patch("midflight.theater.hosted_reviewer.shutil.which", return_value="/path/codex"),
        patch("midflight.theater.hosted_reviewer._run_cli", side_effect=run),
        patch.object(PeerReviewPolicy, "review_claim", review),
        patch("midflight.theater.hosted_reviewer.time.monotonic", side_effect=[100, 125]),
        pytest.raises(ReviewerUnavailable),
    ):
        reviewer.review_claim(None)
    assert timeouts == [5]
    assert reviewer._deadline is None


def test_timeout_kills_the_cli_wrapper_and_its_child(tmp_path):
    import os
    import sys
    import time

    import pytest

    from midflight.theater.hosted_reviewer import _run_cli

    pidfile = tmp_path / "child.pid"
    program = (
        "import subprocess,sys,time; "
        "from pathlib import Path; "
        "p=subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)']); "
        f"Path({str(pidfile)!r}).write_text(str(p.pid)); "
        "time.sleep(30)"
    )
    started = time.monotonic()
    with pytest.raises(subprocess.TimeoutExpired):
        _run_cli([sys.executable, "-c", program], prompt="", cwd=tmp_path, timeout=1)
    assert time.monotonic() - started < 5
    pid = int(pidfile.read_text())
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return
    # A killed child may remain briefly as a zombie awaiting its OS reaper.
    state = subprocess.run(
        ["ps", "-p", str(pid), "-o", "stat="], capture_output=True, text=True
    ).stdout.strip()
    assert not state or state.startswith("Z")


def test_concurrent_reviews_have_isolated_deadlines_and_failures():
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from midflight.theater.review_policy import PeerReviewPolicy

    reviewer = HostedReviewer()
    barrier = Barrier(2)

    def review(self, request):
        if request == "fail":
            self._failure = ReviewerUnavailable("failed transport")
        barrier.wait(timeout=3)
        return {"findings": []}

    with patch.object(PeerReviewPolicy, "review_claim", review), ThreadPoolExecutor(2) as pool:
        fail = pool.submit(reviewer.review_claim, "fail")
        good = pool.submit(reviewer.review_claim, "good")
        with pytest.raises(ReviewerUnavailable):
            fail.result()
        assert good.result() == {"findings": []}
