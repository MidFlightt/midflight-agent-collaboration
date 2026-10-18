"""No model/database calls: preparation, frozen prompts and opt-in safeguards."""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "experiment" / "communication"


def load_case():
    spec = importlib.util.spec_from_file_location(
        "communication_benchmark_case", SCRIPTS / "case.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_three_arms_preserve_notes_and_remove_legacy_workflow():
    case = load_case()
    for arm in "NAB":
        for agent, (phase, note) in case.old.DEVELOPER_NOTE.items():
            assert note in case.prompt(arm, agent, phase, "test")
    text = "\n".join(
        case.prompt("B", a, p, "test") for p, agents in case.PHASES.items() for a in agents
    )
    for forbidden in ("submit_claim", "approve_plan", "resolve_escalation", "project_id"):
        assert forbidden not in text
    assert case.lead("B", "plan", "test") is None
    assert "express-policy" in case.lead("B", "change", "test")["prompt"]
    assert case.old.plan.change_message() in case.prompt("N", "t6", 3, "test")


def test_prepare_and_overwrite_protection(tmp_path):
    bundle = tmp_path / "bundle"
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "prepare.py"), str(bundle)], capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    manifest = json.loads((bundle / "manifest.json").read_text())
    assert manifest["status"] == "prepared-not-run"
    assert set(json.loads((bundle / "prompts.json").read_text())) == set("NAB")
    assert not (bundle / "runs").exists()
    assert not (bundle / "case/results").exists()
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "prepare.py"), str(bundle)], capture_output=True, text=True
    )
    assert result.returncode != 0


@pytest.mark.parametrize("arm", ["N1", "A1", "B1"])
def test_execution_requires_explicit_opt_in(tmp_path, arm):
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "run.py"), str(tmp_path), arm],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert "--execute is required" in result.stderr
    assert list(tmp_path.iterdir()) == []


def test_current_publication_objection_semantics():
    case = load_case()
    assert {t.rsplit("__", 1)[-1] for t in case.TOOLS} == {"join", "send", "check_in", "object"}
    text = case.coordination("t3")
    for required in (
        "publication_id",
        "revision",
        "affects",
        "kind=resolve",
        "Only the objection author",
        "without approval",
        "without acknowledging",
    ):
        assert required in text
    assert "agree(" not in text and "negotiate proposals" not in text
    assert case.PHASES[3][-1] == "t6"
    assert "t6" not in case.PHASES[1] and "t6" not in case.PHASES[2]


def test_report_keeps_unknown_usage_unknown(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(SCRIPTS))
    import report

    logs = tmp_path / "logs"
    logs.mkdir()
    (tmp_path / "state.json").write_text('{"scores":[]}')
    (logs / "01-t1.result.json").write_text(
        json.dumps(
            {
                "category": "building",
                "usage": {"input_tokens": 10, "output_tokens": 4},
                "agent": "t1",
                "status": "completed",
                "returncode": 0,
            }
        )
    )
    output = report.summarize(tmp_path)
    assert output["usage"]["all_in"]["usage"]["input_tokens"] == 10
    assert output["usage"]["all_in"]["usage"]["cached_input_tokens"] is None
    assert output["usage"]["all_in"]["actual_cost_usd"] is None
    assert output["first_merge"] is None


def test_atomic_state_reads_during_save(tmp_path, monkeypatch):
    import threading

    monkeypatch.syspath_prepend(str(ROOT))
    from experiment.run import Trial

    trial = Trial("pigeonpost", "Natomic")
    trial.root = tmp_path
    trial.save({"n": 0, "padding": "x" * 100000})
    errors = []

    def reader():
        for _ in range(200):
            try:
                assert "n" in trial.state()
            except Exception as error:
                errors.append(error)

    thread = threading.Thread(target=reader)
    thread.start()
    for n in range(50):
        trial.save({"n": n, "padding": "x" * 100000})
    thread.join()
    assert not errors


def test_codex_cumulative_usage_is_not_double_counted(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(SCRIPTS))
    import report

    logs = tmp_path / "logs"
    logs.mkdir()
    (tmp_path / "state.json").write_text('{"scores":[]}')
    for i, total in enumerate([100, 140, 180]):
        (logs / f"{i:02d}.result.json").write_text(
            json.dumps(
                {
                    "category": "building",
                    "agent": "t1",
                    "session_id": "same",
                    "usage": {
                        "input_tokens": total,
                        "output_tokens": total // 10,
                        "cached_input_tokens": total // 2,
                        "cache_write_input_tokens": 0,
                    },
                    "status": "completed",
                    "returncode": 0,
                }
            )
        )
    result = report.summarize(tmp_path)
    assert result["usage"]["all_in"]["usage"]["input_tokens"] == 180
    assert result["usage"]["all_in"]["usage"]["output_tokens"] == 18
    assert result["usage"]["all_in"]["usage"]["cache_write_input_tokens"] == 0


def test_chat_uses_separate_git_storage_and_preserves_worktree(tmp_path):
    import concurrent.futures

    origin = tmp_path / "origin.git"
    repo = tmp_path / "repo"
    subprocess.run(["git", "init", "--bare", "-q", str(origin)], check=True)
    subprocess.run(["git", "clone", "-q", str(origin), str(repo)], check=True, capture_output=True)
    for key, value in [("user.name", "test"), ("user.email", "test@example.com")]:
        subprocess.run(["git", "config", key, value], cwd=repo, check=True)
    (repo / "CHAT.md").write_text("# Team chat\n\n")
    subprocess.run(["git", "add", "CHAT.md"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "initial"], cwd=repo, check=True)
    subprocess.run(["git", "push", "-q", "origin", "HEAD:chat"], cwd=repo, check=True)
    before = {
        str(p.relative_to(repo)): p.read_bytes() for p in (repo / ".git").rglob("*") if p.is_file()
    }

    def post(n):
        return subprocess.run(
            [sys.executable, str(SCRIPTS / "chat.py"), "post", f"T{n}: update"],
            cwd=repo,
            capture_output=True,
            text=True,
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(post, range(3)))
    assert all(r.returncode == 0 for r in results), results
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "chat.py"), "read"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    assert all(result.stdout.count(f"T{n}: update") == 1 for n in range(3))
    after = {
        str(p.relative_to(repo)): p.read_bytes() for p in (repo / ".git").rglob("*") if p.is_file()
    }
    assert before == after


def test_v6_removes_forced_checkins_without_changing_other_arms():
    case = load_case()
    for phase, agents in case.PHASES.items():
        for agent in agents:
            text = case.prompt("B", agent, phase, "fresh-run-graph")
            assert "Check in with Midflight first" not in text
            assert "Check in before work and before finishing" not in text
    text = case.coordination("t1")
    assert "drain more=true" in text
    assert "natural work boundary" in text
    assert "without acknowledging" in text
