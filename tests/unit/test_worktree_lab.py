import subprocess
from pathlib import Path

import pytest
from fastapi import HTTPException

from demo_fixture import NOW
from midflight.adapters.clock import FixedClock
from midflight.adapters.memory_store import MemoryStore
from midflight.api.app import build_services
from midflight.domain.models import Contract, FieldType, Task
from midflight.services.plans import PlanDraft
from midflight.theater.peer_coordination import PeerCoordination
from midflight.theater.worktree_lab import NAMES, PROMPTS, create_repository, seed_lab


@pytest.fixture
def coordination():
    services = build_services(MemoryStore(), FixedClock(NOW))
    seed_lab(services, "lab")
    return PeerCoordination(services, "lab", names=NAMES, preserve_tasks=False)


def test_lab_starts_without_contracts_or_task_dependencies(coordination):
    plan = coordination.read("web")
    assert plan.contracts == []
    assert {t.owner for t in plan.tasks} == set(NAMES)
    assert all(not t.provides and not t.consumes for t in plan.tasks)
    assert all(len(prompt.split()) < 20 and "TASK.md" not in prompt for prompt in PROMPTS.values())


def test_agent_can_introduce_an_interface_and_expand_its_task_scope(coordination):
    plan = coordination.read("api")
    contract = Contract(
        id="task-item",
        version=1,
        provider_task="api",
        consumer_tasks=["web"],
        fields={"title": FieldType.STRING},
    )
    tasks = [
        t.model_copy(update={"provides": [contract.id]})
        if t.id == "api"
        else t.model_copy(update={"consumes": [contract.id]})
        if t.id == "web"
        else t
        for t in plan.tasks
    ]
    tasks.append(
        Task(id="smoke", title="Exercise the running app", owner="docs", branch="agent-docs")
    )
    approved, replayed = coordination.publish(
        "api",
        1,
        "Declare task item interface",
        PlanDraft(requirements=plan.requirements, tasks=tasks, contracts=[contract]),
    )
    assert approved.version == 2 and not replayed
    assert approved.contracts[0].id == "task-item"
    assert any(t.id == "smoke" for t in approved.tasks)
    assert coordination.read("web").version == 2
    with pytest.raises(HTTPException) as error:
        coordination.publish(
            "cli",
            1,
            "Stale edit",
            PlanDraft(requirements=plan.requirements, tasks=plan.tasks, contracts=[]),
        )
    assert error.value.status_code == 409


def test_new_tasks_cannot_be_assigned_to_an_unknown_participant(coordination):
    plan = coordination.read("api")
    with pytest.raises(HTTPException) as error:
        coordination.publish(
            "docs",
            1,
            "Add task",
            PlanDraft(
                requirements=plan.requirements,
                tasks=[*plan.tasks, Task(id="unknown", title="No actor", owner="outsider")],
                contracts=[],
            ),
        )
    assert error.value.status_code == 422


def test_four_worktrees_share_history_but_keep_uncommitted_files_separate(tmp_path):
    repository = create_repository(tmp_path)
    common = []
    for name in NAMES:
        worktree = tmp_path / name
        assert (worktree / ".git").is_file()
        raw = subprocess.check_output(
            ["git", "-C", str(worktree), "rev-parse", "--git-common-dir"], text=True
        ).strip()
        path = Path(raw)
        common.append(path.resolve() if path.is_absolute() else (worktree / path).resolve())
    assert len(set(common)) == 1
    assert common[0] == repository / ".git"
    (tmp_path / "api" / "server.py").write_text("print('real application code')\n")
    assert not (tmp_path / "web" / "server.py").exists()
    git = [
        "git",
        "-C",
        str(tmp_path / "api"),
        "-c",
        "user.name=Lab",
        "-c",
        "user.email=lab@localhost",
    ]
    subprocess.run([*git, "add", "server.py"], check=True)
    subprocess.run([*git, "commit", "-qm", "Build API"], check=True)
    shared = subprocess.check_output(
        ["git", "-C", str(tmp_path / "web"), "show", "agent-api:server.py"], text=True
    )
    assert "real application code" in shared
    assert not (tmp_path / "web" / "server.py").exists()


def test_real_codex_profile_allows_worktree_commits_and_http_but_blocks_peer_writes(tmp_path):
    import shutil
    import sys

    from midflight.theater.worktree_lab import worktree_permissions

    codex = shutil.which("codex")
    if sys.platform != "darwin" or not codex:
        pytest.skip("macOS Codex sandbox integration requires the local CLI")
    create_repository(tmp_path)
    (tmp_path / "api" / "server.py").write_text("print('api')\n")
    args = worktree_permissions(tmp_path, "api")
    # sandbox subcommand selects its profile explicitly; the TUI uses default_permissions.
    args = ["-P", "worktree-lab", *args[2:]]
    probe = """
import pathlib, socket, subprocess
subprocess.run(['git','add','server.py'], check=True)
subprocess.run(['git','commit','-qm','Implement API'], check=True)
with socket.socket() as server:
    server.bind(('127.0.0.1', 0))
try:
    pathlib.Path('../web/forbidden.txt').write_text('must not happen')
except PermissionError:
    pass
else:
    raise AssertionError('Peer workspace was writable')
"""
    result = subprocess.run(
        [codex, "sandbox", *args, "-C", str(tmp_path / "api"), "--", sys.executable, "-c", probe],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert not (tmp_path / "web" / "forbidden.txt").exists()
    shared = subprocess.check_output(
        ["git", "-C", str(tmp_path / "web"), "show", "agent-api:server.py"], text=True
    )
    assert shared == "print('api')\n"
