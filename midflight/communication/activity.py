"""Factual tool-result footer for collapsed terminal previews; no inferred agent state."""


def excerpt(value, limit=180):
    value = " ".join(value.split())
    return value if len(value) <= limit else value[: limit - 1] + "…"


def activity(operation, result, args):
    context = result.get("updates", result)
    actor = context["agent"]
    if operation == "send":
        _, kind, body, _, _, topic, reply_to, *_ = args
        verbs = {
            "interface": "published interface",
            "policy": "published policy",
            "implementation": "reported implementation",
            "applied": "reported application",
            "verification": "reported test evidence",
            "resolve": "resolved own objection",
        }
        verb = verbs.get(kind, "sent " + kind)
        target = f" {topic} r{result['revision']}" if kind in {"interface", "policy"} else ""
        reference = f" referencing #{reply_to}" if reply_to is not None else ""
        peers = ", ".join(result["recipients"]) or "no subscribers"
        retry = "Retry: existing event; not sent again. " if result.get("duplicate") else ""
        summary = (
            f"{retry}{actor}: {verb}{target}{reference} → {peers} "
            f"(event #{result['event_id']}). Agent wrote: {excerpt(body)}"
        )
    elif operation == "object":
        _, publication_id, revision, problem, affects, *_ = args
        summary = (
            f"{actor}: objection #{result['objection_id']} to publication "
            f"#{publication_id} r{revision}. Problem: {excerpt(problem, 110)} "
            f"Affects: {excerpt(affects, 80)}"
        )
        if result.get("duplicate"):
            summary = "Retry: existing objection; not created again. " + summary
    else:
        summary = f"{actor}: " + (
            "session context returned." if operation == "join" else "checkpoint updates returned."
        )

    incoming = [e for e in context.get("messages", []) if e["author"] != actor]
    if incoming:
        e = incoming[-1]
        summary += (
            f" Returned {len(incoming)} peer update(s); latest #{e['id']} "
            f"from {e['author']} ({e['kind']}): {excerpt(e['body'])}"
        )
    elif operation in {"join", "check_in"}:
        interfaces = context.get("interfaces", [])
        if interfaces:
            e = interfaces[-1]
            summary += (
                f" Shared interface #{e['id']} {e['topic']} r{e['revision']}: {excerpt(e['body'])}"
            )
        else:
            summary += " No peer updates or published interfaces in this response."
    if context.get("unapplied_policies"):
        policy = context["unapplied_policies"][-1]
        summary += (
            f" Unapplied policy #{policy['id']} r{policy['revision']}: "
            f"{excerpt(policy['body'], 100)}"
        )
    if context.get("more"):
        summary += " More updates remain; this is only one page."
    if context.get("open_objections"):
        summary += f" {len(context['open_objections'])} unresolved objection(s) in context."
    return summary
