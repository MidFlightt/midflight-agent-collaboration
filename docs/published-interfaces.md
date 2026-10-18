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

A consumer sends `kind="objection"`, `reply_to=published_interface_event_id`, and a
concrete incompatibility. The record captures the exact interface revision; it is sent
to the current owner and subscribers and remains in relevant checkpoint context.
Discussion uses ordinary messages or questions. Publishing a new interface, reading
an objection, transferring ownership or mutually agreeing to a proposal does not close it.

The objection's author sends `kind="resolve"`, `reply_to=objection_event_id`, with an
explanation/evidence. That resolves the record and notifies its audience, including the
current owner after a handoff. There is no deadline, automatic acceptance, silent expiry
or forced choice by MidFlight. The last publication remains available beside the open
objection. Agents can continue unrelated work and identify the affected work they cannot
safely finish. If human requirements conflict, ask the human rather than guessing.

`proposal` and `agree` retain their exact-revision semantics for optional negotiations.
Even a fully agreed proposal does not itself publish a contract: the responsible owner
publishes the resulting interface if needed. Agents are instructed not to use this
ceremony for ordinary interfaces they can simply follow.

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
`check_in` and `agree` return that context too. A session records
`delivered_interface_revisions`; each interface response includes
`previously_delivered_revision`. This means the server sent the revision, not that the
agent received a lost response, understood it, adopted it in code, or agreed to it.
Each session's delivery metadata and cursor are independent and durable.

There are no repeated prompts, idle check-in loops or wakeups. An idle peer's cursor
and delivery metadata remain unchanged until its next useful turn. The service can
retain pending work indefinitely. Do not call an update complete merely because the
sender published it or independently combined code passes tests.

## Compatibility and validation

The four-tool surface remains `join`, `send`, `check_in`, `agree`; new behavior is carried
by send kinds and the optional `new_owner` argument. Legacy communication state gains
empty owner/interface/objection maps on its next write. Existing requests retain their
fingerprints. Legacy proposals are not silently promoted to published interfaces and
retained runs are not automatically assigned owners. New reset runs get seeded ownership;
restart MCP processes to load the new tool schema/instructions.

Real FalkorDB tests cover concurrent publications, wrong-owner declarations, optional
agreements, objections surviving restarts and revisions, author-only resolution,
transfers, late subscribers, independent delivery metadata, policy-only changes and
database SIGKILL recovery. Real stdio processes verify publication and use without agree.

See [rehearsal evidence](evidence/published-interfaces.md) for measured behavior and
limitations, including a first run that unnecessarily revised an interface because it
contained the initial refund formula.
