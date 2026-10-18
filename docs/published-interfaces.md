# Published interfaces without routine mutual agreement

A named interface owner publishes a revision with `send(kind="interface", topic=...,
expected_revision=..., body=...)`. The first revision becomes the default immediately;
consumers read it and work against it. No proposal, acceptance or model review is needed.
Publication is a declaration, not proof that code is correct. Test the combined code.

## Ownership and simultaneous writes

Project setup assigns interface responsibility with the operator-only
`Service.configure_interfaces({topic: agent_name})`. It is not a fifth agent tool and
cannot overwrite an existing assignment. The delivery fixture assigns Delivery the
record interface, Booking the request interface and Notifications confirmation.
The ownership directory is returned to all sessions; interface content remains scoped
to owners and dependency subscribers. Unknown ownership requires an operator assignment;
an agent can share an intention meanwhile, but arriving first does not grant authority.

A consumer cannot replace the owner's interface. Two owner sessions publishing against
the same revision race through the existing atomic CAS: one succeeds, the other rereads
and gets a stale-revision error. Identical request retries still return the original
receipt. The first publication expects revision 0; subsequent ones expect the current
interface revision. This is concurrency control, not approval of content.

Only the current owner can send `kind="transfer"`, specifying `topic`, `new_owner`,
`expected_revision` of **ownership**, and an explanation. Ownership revisions begin at 1
and advance independently of interface revisions. Transfer does not rewrite the contract
or resolve objections. The new owner gets current context even without a subscription.
These are trusted local labels, not authenticated multi-tenant permissions.

## Disagreement without a blanket work gate

A consumer calls `object(session_id, publication_id, revision, problem, affects,
request_id, alternative="")`. The affected publication must be an exact interface or
policy event/revision. `affects` identifies the requirement or dependency that is broken;
a solution is optional. The stable objection ID is routed to the publisher, original
publication audience, current subscribers and current interface owner if any. An unrelated
agent cannot object to an invisible publication. Historical revisions may be challenged.
Discussion uses ordinary messages or questions. Publication, supersession, ownership
transfer, passing tests, reading and silence never resolve the objection.

The objection's author sends `kind="resolve"`, `reply_to=objection_event_id`, with an
explanation/evidence. That resolves the record and notifies its audience, including the
current owner after a handoff. There is no deadline, automatic acceptance, silent expiry
or forced choice by MidFlight. The last publication remains available beside the open
objection. Agents can continue unrelated work and identify the affected work they cannot
safely finish. If human requirements conflict, ask the human rather than guessing.

Ownership is responsibility, not authority to override another component's requirements.
Agents may adapt directly if the boundary satisfies their requirements, without any
acknowledgement. Objections are persistent signals, not vetoes or global approval gates.
Report open incompatibilities alongside results for the affected integration; continue
unaffected work and escalate genuinely unresolved decisions to the human.

## Policy changes and natural checkpoints

Keep stable signatures, shape, errors and calling conventions in the interface.
Keep changeable business rules in policy messages. For example, a saved refund field
follows current policy; the interface should not embed the current cancellation fee.
A fee change alone requires no API revision when callers still use the same saved fields.
The agent interpreting the human's instruction identifies the affected topic; MidFlight
only routes it through explicit dependencies. It does not classify prose using a model.

Booking subscribes to `delivery-record` as well as `booking-request` because it reads
server response fields. It does **not** subscribe to `cancellation-policy`. Billing and
Delivery do. This delivers genuine record-shape changes to Booking without sending fee
policy updates. Agents still must correctly separate these topics; arbitrary prose
classification is not an enforcement guarantee.

`join` recovers relevant current publications and outstanding objections. `send`,
`check_in` and `object` return that context too. A session records
`delivered_interface_revisions`; each interface response includes
`previously_delivered_revision`. This means the server sent the revision, not that the
agent received a lost response, understood it, adopted it in code, or agreed to it.
Each session's delivery metadata and cursor are independent and durable.

There are no repeated prompts, idle check-in loops or wakeups. An idle peer's cursor
and delivery metadata remain unchanged until its next useful turn. The service can
retain pending work indefinitely. Do not call an update complete merely because the
sender published it or independently combined code passes tests.

## Compatibility and validation

The active tools are `join`, `send`, `check_in`, `object`. No proposal or agreement write
path remains. Historical events, proposal/acceptance state and retry receipts are retained
verbatim; they are not returned as actionable proposals or promoted to interfaces. Old
send-objection records remain visible and author-resolvable, without invented requirements.
Existing send fingerprints are retained for unchanged operations. New reset runs get seeded
ownership; existing MCP processes need restart to load the new schema. Existing runs are
never rewritten or reset automatically.

Real FalkorDB tests cover exact interface and policy objections, optional alternatives,
wrong revisions, author-only resolution, concurrent publication/retries, supersession,
independent session delivery, ownership transfers and crash recovery. Real stdio tests
verify exactly four tools and recovered objections. Operator integration results include
open objections even when every test passes; they never close objections themselves.
