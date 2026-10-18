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
