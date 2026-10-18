from midflight.communication.activity import activity


def test_join_preview_exposes_peer_content_without_inventing_realignment():
    result = {
        "updates": {
            "agent": "billing",
            "messages": [
                {
                    "id": 3,
                    "author": "delivery",
                    "kind": "interface",
                    "body": "Return ID-keyed mapping",
                }
            ],
        }
    }
    text = activity("join", result, ())
    assert "Return ID-keyed mapping" in text
    assert "Returned 1 peer update" in text
    assert "realigned" not in text and "applied" not in text


def test_implementation_preview_attributes_exact_report_and_retry():
    result = {
        "event_id": 5,
        "revision": 0,
        "recipients": ["delivery"],
        "duplicate": True,
        "updates": {"agent": "billing", "messages": []},
    }
    text = activity(
        "send",
        result,
        (
            "session",
            "implementation",
            "Expected list; switched to mapping.values()",
            "id",
            None,
            "",
            3,
        ),
    )
    assert "not sent again" in text
    assert "reported implementation referencing #3" in text
    assert "Expected list; switched to mapping.values()" in text


def test_preview_keeps_unresolved_and_pagination_visible():
    result = {"agent": "billing", "messages": [], "more": True, "open_objections": [{"id": 4}]}
    text = activity("check_in", result, ())
    assert "More updates remain" in text and "1 unresolved objection" in text


def test_object_retry_is_not_a_new_problem():
    result = {"objection_id": 4, "duplicate": True, "updates": {"agent": "billing"}}
    text = activity("object", result, ("session", 3, 2, "Missing saved refund", "Revenue", "id"))
    assert "not created again" in text and "#3 r2" in text and "Revenue" in text
