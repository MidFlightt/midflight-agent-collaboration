from types import SimpleNamespace

from fastapi.testclient import TestClient

from midflight.theater.source_view import WorkspaceObserver, create_app


def test_files_are_observed_on_disk_not_from_claims(tmp_path):
    workspace = tmp_path / "alice"
    workspace.mkdir()
    (workspace / "a.py").write_text("value = 1\n")
    (workspace / "TASK.md").write_text("fixture")
    observer = WorkspaceObserver()
    files, events, errors = observer.scan(tmp_path, "run", ["alice"])
    assert [f["label"] for f in files] == ["a.py"]
    assert files[0]["origin"] == "filesystem"
    assert files[0]["observation"] == "present"
    assert events == errors == []
    original_hash = files[0]["sha256"]
    (workspace / "b.py").write_text("new = True\n")
    (workspace / "a.py").write_text("value = 2\n")
    files, events, _ = observer.scan(tmp_path, "run", ["alice"])
    assert {(e["path"], e["type"]) for e in events} == {("a.py", "modified"), ("b.py", "created")}
    assert next(f for f in files if f["label"] == "a.py")["sha256"] != original_hash
    (workspace / "a.py").unlink()
    files, events, _ = observer.scan(tmp_path, "run", ["alice"])
    assert [f["label"] for f in files] == ["b.py"]
    assert events[-1]["type"] == "removed"
    _, repeated, _ = observer.scan(tmp_path, "run", ["alice"])
    assert repeated == events
    _, reset, _ = observer.scan(tmp_path, "fresh", ["alice"])
    assert reset == []


def test_symlinks_private_directories_and_late_workspace_baselines_are_excluded(tmp_path):
    outside = tmp_path / "secret.py"
    outside.write_text("private = True\n")
    workspace = tmp_path / "alice"
    workspace.mkdir()
    (workspace / "linked.py").symlink_to(outside)
    (workspace / ".git").mkdir()
    (workspace / ".git" / "private.py").write_text("hidden")
    (workspace / "node_modules").mkdir()
    (workspace / "node_modules" / "noise.js").write_text("noise")
    observer = WorkspaceObserver()
    assert observer.scan(tmp_path, "run", ["alice", "../escape"])[0] == []
    (tmp_path / "bob").mkdir()
    (tmp_path / "bob" / "existing.py").write_text("already existed")
    files, events, _ = observer.scan(tmp_path, "run", ["alice", "bob"])
    assert [f["label"] for f in files] == ["existing.py"]
    assert events == []


def test_observer_exposes_no_demo_mutation_routes():
    view = SimpleNamespace(key="secret", upstream="http://127.0.0.1:8907", snapshot=lambda: {})
    with TestClient(create_app(view), base_url="http://localhost") as client:
        assert client.get("/graph-state").status_code == 403
        assert (
            client.get("/connection", headers={"sec-fetch-site": "cross-site"}).status_code == 403
        )
        assert client.get("/graph-state", headers={"x-demo-key": "secret"}).json() == {}
        for route in ("/reset", "/peer-start", "/peer-plan", "/direction"):
            assert client.post(route).status_code == 404


def test_read_failure_is_not_reported_as_file_deletion(tmp_path, monkeypatch):
    from pathlib import Path

    workspace = tmp_path / "alice"
    workspace.mkdir()
    (workspace / "a.py").write_text("real file")
    observer = WorkspaceObserver()
    observer.scan(tmp_path, "run", ["alice"])

    def fail_read(self):
        raise PermissionError("not readable")

    monkeypatch.setattr(Path, "read_bytes", fail_read)
    files, events, errors = observer.scan(tmp_path, "run", ["alice"])
    assert files[0]["observation"] == "unavailable"
    assert events == []
    assert errors
