# Agent communication migration

## Scope and preservation

Only `MidFlightt/midflight-agent-collaboration` changes. The migration branch is
`codex/agent-communication`, based on GH-05 commit `53e6238`. Commit `61d746f`
first preserves all fourteen modified/untracked GH-05 files, including the warm
reviewer and latency tests. `preservation.json` records their original hashes.
The original `/tmp/midflight-peer-demo` remains on GH-05 with its changes intact.
Other collaboration worktrees, including the map-stage work in progress, are untouched.
The official `MidFlightt/MidFlight` repository is not edited.

The behavioral reference is `/Users/frederikjonsson/Documents/ChatGPT/Midflight`.
Its source is untouched; its 37 tests were rerun with bytecode and pytest cache
writes disabled and passed in 7.53 seconds. This migration implements its four
communication operations and durability invariants, not its SQLite lifecycle hooks
that broadcast raw developer inputs. There is no silent conversion of legacy graphs.

## Architecture proposed before implementation

1. Preserve the peer work and branch separately before edits.
2. Implement an independent four-tool service on FalkorDB; verify atomic retries,
   exact revision agreement, session cursors and crash recovery before terminal use.
3. Add explicit dependency edges and selective policy routing. Coding agents provide
   interpretation; the service never invokes a model or decides interface content.
4. Reuse the four-terminal tmux/WebSocket transport, replace its MCP connection and
   remove reviewer/claim status UI. Preserve runs on reset and stage unsent prompts.
5. Run actual agents against incompatible starters, combine their owned modules,
   introduce the fee change, and measure messages, code changes and real tests.

## Owner publication follow-up

The current default is owner publication, not unanimous acceptance. See
[published interface behavior](published-interfaces.md) for ownership, objections,
transfers, delivery metadata and the no-wakeup rehearsal. Earlier agreement-based
rehearsals below remain historical evidence; they do not prescribe the current workflow.

## Storage and consistency

One graph represents one run. `CState` contains a monotonically increasing revision
and canonical JSON containing members, sessions, events and
retry receipts, interface owners, published interfaces and open objections. `CAgent` and `CTopic` nodes with `DEPENDS_ON` edges form the routing
projection. This deliberately small-project design keeps the behavior auditable:
all state and projection changes occur in one atomic, revision-guarded Cypher write.
There is no process-local coordination lock or expiring distributed writer lease.
A competing write causes the service to reread, recompute routing and retry its CAS.

A receipt is keyed by agent plus request ID and fingerprints the full request.
An identical retry returns its original result; different input is rejected. State
mutations and receipt insertion cannot commit separately. Transport errors propagate
without automatic write replay. Retry uncertain writes with the same request ID.
Inbox responses advance durable per-session cursors; replay a lost response with
`check_in(after=last_received_cursor)`. Pagination filters recipients before slicing.
A new chat gets a separate cursor and recovers current publications and outstanding work.

`object` records a problem with an exact published interface or policy revision and an
affected requirement/dependency; an alternative is optional. Only its author can resolve
via structured send. Objections survive new publications, tests, transfers and silence.
Historical proposal/acceptance records are preserved but no active agreement machinery
remains. See [current publication behavior](published-interfaces.md) for the four-tool API.

## Dependency routing

`join(dependencies=[...])` replaces that agent's explicit topic subscriptions;
omitting the argument retains them. `send(kind="dependency", topic=..., depends_on=[...])`
declares topic prerequisites. Topic edges point toward prerequisites; the routing
query finds subscribers of the changed topic and its transitive dependants.
Cycles and paths deeper than 32 edges are rejected. Subscriptions are not inferred
from prose, file names, ownership claims or a model.

The demo seeds these dependencies:

| Agent | Topics |
| --- | --- |
| Billing | delivery-record, cancellation-policy |
| Delivery | delivery-record, booking-request, cancellation-policy |
| Booking | booking-request, delivery-record |
| Notifications | confirmation |

This distinction matters: cancellation semantics can change without changing the
booking request or record shape. Traversing every task that uses Delivery would
unnecessarily notify Booking. The coding agent names the changed topic; the graph
then selects recipients. Explicit recipients are available for peer negotiation.
Topic updates cannot override graph recipients with `to`. Replies retain their original
audience plus current subscribers; direct messages omit topic. No recipient list defaults to broadcast.

Human-source text on policies is attributed by the coding agent, not independently
authenticated. Names and sessions are trusted local identifiers. An arbitrary peer
message can still contain arbitrary text; this is coordination, not a semantic
information-flow security boundary. Correct topic declarations remain essential.

## Terminals, reset and recovery

The current entrypoint and the former `midflight.theater.peers` command both launch
`communication.harness`. Historical reviewer classes stay available only for legacy
experiments/tests; the new harness never constructs their service or reviewer.
The terminal page displays actual terminal bytes with optional, reversible syntax
highlighting. It adds no verdicts, claim badges or scripted agent narration. `/report` displays recorded state
and saved independently executed test results; viewing it does not run a model.

Each agent has a persistent Codex session and a short prepared prompt. Check-ins
occur at useful work boundaries; sending a message also returns available updates.
There is no periodic agent polling or auto-turn scheduler. An idle agent needs an
explicit notification or the human's next task prompt. The measured validation
used one neutral notification to Billing in the earlier rehearsals. The owner-publication
follow-up leaves Billing idle, with the policy pending; no notification is sent.

Reset saves the current report, marks the old run archived, closes its tmux session,
retains code/tests/profiles and the entire graph, then creates a fresh run and
prepares prompts without pressing Enter. Run directories and profiles are ignored
by Git. Recovery with `--resume` reattaches the existing tmux session and graph;
it neither seeds new members nor submits prompts. If terminals are absent, it fails
explicitly rather than pretending coding context was recovered.

## Validation and limits

See [measured results](evidence/README.md) and the evidence directories for actual component code, tests, combined snapshots,
coordination records and measured turn times. The first rehearsal exposed an explicit
recipient loophole: Delivery addressed its fee application report to Booking. The
policy itself was selective and Booking never woke or changed code, but that was
not full message isolation. The service now rejects that audience expansion; a
regression test and a second real-agent rehearsal exercise the corrected behavior.

The independent validator tests generated functions together, including saved
refund revenue, zero and below-fee totals, repeated cancellation, snapshot isolation,
booking requests and notification generation. It is not a full deployed browser
or production end-to-end test. Component tests may use local mocks; their passing
alone is not evidence of integration. The validator currently follows the negotiated
selected `id` or `delivery_id` shape and would need adaptation for other valid contracts.

The JSON snapshot is rewritten on every operation, including cursor advancement;
there is a single project-level CAS contention point and no retention/compaction.
This is suitable for the four-agent hackathon experiment, not proven at large scale.
Raw human input capture, production authentication, cross-project permissions and
automatic idle-agent wakeups are deliberately absent. No comparative speedup versus
the previous reviewer design has been measured.

Terminal highlights use blue for MidFlight calls, orange for other-agent mentions, and red for objection calls and references. Colors label the actual terminal text; they do not establish objection state or correctness.
