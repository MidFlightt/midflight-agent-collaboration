"""The operator CLI must not hide a failing component behind a passing combined test."""

import pytest

from midflight.communication import validate


def test_component_failure_makes_validator_cli_fail(monkeypatch, tmp_path):
    monkeypatch.setattr("sys.argv", ["validate", str(tmp_path)])
    monkeypatch.setattr(
        validate,
        "validate",
        lambda *args: {
            "combined": {"returncode": 0},
            "components": {"billing": {"returncode": 1}, "delivery": {"returncode": 0}},
        },
    )
    with pytest.raises(SystemExit) as error:
        validate.main()
    assert error.value.code == 1


def test_saved_success_is_stale_after_module_changes(tmp_path):
    import hashlib

    from midflight.communication.validate import NAMES, evidence_status

    hashes = {}
    for name in NAMES:
        folder = tmp_path / name
        folder.mkdir()
        source = folder / (name + ".py")
        source.write_text("# tested bytes\n")
        hashes[name] = hashlib.sha256(source.read_bytes()).hexdigest()
    evidence = {"success": True, "executed_by": "operator", "hashes": hashes}
    assert evidence_status(tmp_path, evidence)["matches_current_modules"]
    (tmp_path / "billing/billing.py").write_text("# changed after validation\n")
    result = evidence_status(tmp_path, evidence)
    assert not result["matches_current_modules"]
    assert evidence == {"success": True, "executed_by": "operator", "hashes": hashes}


def test_actual_starters_cannot_report_integration_success(tmp_path):
    from midflight.communication.validate import NAMES
    from midflight.theater.delivery_fixture import write_starter

    for name in NAMES:
        write_starter(tmp_path / name, name)
    result = validate.validate(tmp_path)
    assert result["executed_by"] == "operator"
    assert not result["success"]
    assert result["combined"]["returncode"] != 0
    assert all(c["returncode"] == 0 for c in result["components"].values())
