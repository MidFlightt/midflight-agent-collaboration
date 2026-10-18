# Real coding agents against AWS, 2026-10-18 UTC

Four real Codex CLI sessions ran on one computer, with separate workspaces, agent
credentials and durable sessions in isolated project `cloud-rehearsal-20261018`.
All coordination crossed the deployed AWS HTTPS endpoint. This was not a
multi-computer test. The teammate pilot, previous verification project and recorded
local demo were preserved. Raw transcripts and private credentials remain outside Git.

The operator submitted the four initial task prompts once. All initial turns finished
within 53 seconds. Billing initially expected a list; Delivery published event #4,
revision 1, specifying an ID-keyed mapping. Billing adapted its report entry point to
that publication and explained the change in its terminal. No agent raised an objection;
this was direct adaptation, not observed objection/resolution negotiation.

Operator validation copied each agent's owned module unchanged into a fresh subprocess.
All 25 component tests and the combined workflow test passed. Component tests may mock
peers; only the combined test imported all four actual implementations.

The operator then submitted the four-credit fee requirement to Delivery only. Its first
policy write omitted the current revision and was rejected as stale. The agent retried
with expected revision 1 without an operator nudge, publishing policy #12 revision 2.
It changed cancellation to `max(total_cents - 400, 0)` and preserved already saved refunds.
Its fee turn took approximately 20 seconds.

| Evidence stage | Observed result |
| --- | --- |
| Routed | Policy #12 names only Billing and Delivery. |
| Delivered while Billing idle | Delivery received it; Billing's transcript had not. |
| Operator checkpoint | One useful Billing task requested mixed-status/small-total/historical-refund regression coverage. |
| Delivered to Billing | Its resumed session returned policy #12. |
| Read | Billing's work explicitly referenced #12 revision 2 and covered its 400-cent boundary. |
| Application reports | Delivery event #13 and Billing event #14 reference policy #12. |
| Code evidence | Delivery changed the refund formula. Billing added tests; its saved-refund calculation already worked and remained unchanged. |
| Unaffected agents | Booking and Notifications received no fee event. Their owned modules and full session transcripts retained identical hashes. |

Billing's follow-up took approximately 21 seconds. Operator validation then passed all
29 component tests and the combined workflow test with a 400-cent fee. The workflow
covers creating records, booking arguments, cancellation, low/zero totals, repeated
cancellation, revenue, immutable snapshots and confirmation text. It does not prove
production readiness, arbitrary business requirements, or multi-computer behavior.
Passing tests alone are not evidence of Billing consuming the policy; its own session
response, regression work and exact-reference report provide the separate evidence.

No objections were open in the agents' final returned contexts. This run did not exercise
real-agent objections or ownership transfers. Earlier automated cloud transport tests
cover exact objections, author-only resolution, concurrent revisions, retry identity and
independent session recovery. No automatic wakeups, idle-agent polling, forced dialogue,
reviewer or approval gate was used. MidFlight made no model calls; the four coding clients
did. Agent timing and responses are not deterministic.

The harness additions passed the full 605-test suite with an isolated FalkorDB fixture,
Ruff and the panel-highlight JavaScript checks. Cloud-mode Reset is blocked to avoid
clearing shared work; a fresh rehearsal requires a fresh provisioned project. The cloud
report currently does not fetch aggregate server state: objection evidence comes from
session transcripts and is explicitly unavailable to the standalone code validator.

Private local evidence: `runs/cloud-agent-rehearsal/` contains operator actions,
original client transcripts, decoded tool contexts, code/transcript hashes, terminal
captures, both validation runs and measured-results.json. Do not distribute the whole
run directory: client profiles and credentials are private.
