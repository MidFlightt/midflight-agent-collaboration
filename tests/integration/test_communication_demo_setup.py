"""Exercise generated demo workspaces and their real coordination ownership."""

import pytest

from midflight.communication.objection_demo import OverlapObjectionTheater


def test_overlap_starter_has_real_work_and_billing_can_publish(tmp_path, falkor_server):
    live = OverlapObjectionTheater(tmp_path / "demo", falkor_server.port)
    try:
        billing = live.service.join("billing", "Revenue reporting", "test-session")["session_id"]
        result = live.service.send(
            billing,
            "interface",
            "Revenue report returns integer revenue_cents",
            "publish-report",
            topic="revenue-report",
        )
        assert result["event_id"]
        namespace = {}
        exec((tmp_path / "demo/delivery/delivery.py").read_text(), namespace)
        assert namespace["get_delivery_records"]() == {}
        for name, args in (
            ("create_delivery", (1200, "Customer", "Address")),
            ("get_delivery", (1,)),
            ("cancel_delivery", (1,)),
        ):
            with pytest.raises(NotImplementedError):
                namespace[name](*args)
        instructions = (tmp_path / "demo/billing/AGENTS.md").read_text()
        assert "Your owned interface topic is revenue-report." in instructions
    finally:
        live.store.graph.delete()
        live.store.close()
