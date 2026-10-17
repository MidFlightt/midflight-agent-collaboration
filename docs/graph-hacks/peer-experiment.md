# GH-05: equal-peer collaboration experiment

Branch: `GH-05-peer-collaboration`, based on `GH-04-four-agent-demo`.
The existing scripted demo stays on its own branch and port 8897.

Run separately:

```sh
uv sync --locked --extra falkordb --extra demo
uv run --extra falkordb --extra demo python -m midflight.theater.peers
```

Open http://127.0.0.1:8907 (API 8908). Each window starts with a direct request:

- Pricing: “Build pricing for a product that costs $12.”
- Checkout: “Build checkout that creates an order using the product price.”
- Reporting: “Build reporting that returns the total from an order.”
- Notifications: ‘Build a signup confirmation that says "Subscribed: " followed by the email address.’

Each appends “Coordinate with the team through MidFlight.” No prompt asks the agent
to read TASK.md. The shared plan supplies the existing interface details, and TASK.md
retains the same short brief for reference. The commerce tasks are
still a small example project; this experiment generalizes coordination, not project
creation or task allocation. It is not yet an arbitrary-repository installer.

Give a human direction in **any** window. Every peer has `read_shared_plan` and
`publish_shared_plan`. The agent interprets the request and supplies the complete
updated plan. There is no subscription keyword handler or preset plan transformation.
The service validates the plan, records the actual publishing peer, and creates
directives from declared requirements and contract dependencies. Unrelated tasks
receive no directive. Multiple successive changes are supported.

All peers share the same MCP protocol instructions. The short visible prompt does
not eliminate the need for task context or instructions explaining the tools. The
normal claim/check-in protocol lives in MCP; the additional peer instructions explain
how to publish a human-requested plan update. Product choices are made by the agent
from the request, not by a hidden demo script. The agent may ask a clarifying question.

Busy agents discover changes at normal check-ins. After a plan version changes, the
local harness sends each idle peer at most one neutral message: “Check MidFlight for
updates to your task.” It does not include the change, dictate an affected set, or
periodically prompt agents during the initial build. It waits while a terminal is
working or has a typed draft. Sessions persist between stages; Reset starts a fresh
isolated project with the same peer capabilities and preserves earlier run files.

## Guarantees and limits

- Every peer has identical plan-publishing permission in this isolated experiment.
  Internally this reuses the existing domain's LEAD permission for all four identities;
  the production role model and official repository are untouched.
- Publishing requires the plan version the agent read. Concurrent writes are serialized
  through this controller; stale edits return 409 and must be rebased. Identical retries
  of the immediately preceding accepted update return that version without adding one.
- The four task IDs, owners and branches are fixed for the running sessions. Requirements,
  contract fields and task dependency declarations can change. Invalid plans are refused.
- This is a single-controller experiment. Multi-controller publishing and restart-resuming
  an interactive team are not established by this branch's in-memory publish lock.
- The MCP tools use standard stdio and HTTP. The supplied launcher has been tried with
  local Codex; it does not yet provision other computers or validate every agent client.
  Services bind to loopback and are not exposed publicly.
- The coordination page reports actual claims and directives. It deliberately says code
  acceptance is **not assessed**: arbitrary directions need suitable project tests, not
  the old subscription-only integration oracle. Agent-reported tests are not independent
  proof of correctness.
- The experiment consumes model usage. The earlier demo and its ongoing work are preserved.

## Validation

Unit tests cover publishing from each peer, non-subscription changes, identical retries,
stale concurrent updates, invalid identities and task reassignment. The existing suite
also checks the default demo and MCP adapter behavior.

Live rehearsal: a request typed into **Notifications** asked for EUR currency in prices
while keeping the order format unchanged. That peer published plan v2. Pricing and
Checkout received and acknowledged directives; Reporting and Notifications received
none. All four claims were approved. A separate Python integration run confirmed EUR
pricing, the unchanged order shape, reporting and notification output. The independent
rehearsal result is saved with that local run, not presented as a generic test oracle.

## Live graph

Open http://127.0.0.1:8907/graph for a minimal, dark canvas showing only agents.
Agents occupy stable slots in two columns; directed connections have readable labels
such as “Checkout uses Pricing’s output.” Unrelated agents remain separate. Claims,
files, interfaces, directives and row headers are hidden from the canvas. Select an
agent for its claims, declared files and current updates; select a connection for its
exact contract fields and provider/consumer claim IDs.

The vendored `force-graph@1.52.0` library (https://github.com/vasturiano/force-graph)
renders fixed coordinates with physics and node dragging disabled. Pan on empty
space, scroll to zoom, or use Fit and Fullscreen. Agents opens the coding windows.

- Agent presence is persisted in the run's FalkorDB graph when its MCP client connects.
- The raw graph-state endpoint reads the latest persisted claim revisions every 800 ms.
  The browser matches provided and consumed interfaces by contract ID, joins them to
  their claim owners, and renders one provider-to-consumer connection per agent pair.
  Multiple contracts retain separate provenance inside that connection. No links are
  inferred from agent names. A consumed interface without a declared provider creates
  no visual connection; its declaration remains in the raw graph-state data.
- Cyan agents show ordinary scope. A current-plan directive highlights its recipient
  orange while pending or requiring attention, and green once acknowledged. Incident
  dependencies use the same colors, with pending taking precedence. Acknowledgement
  does not prove that implementation or tests passed. Unrelated agents stay unchanged.
- Existing nodes retain fixed coordinates. New nodes append to stable slots without
  shifting their peers or moving the camera. Size growth remains capped.
- Reset archives the run and opens an empty workspace without launching sessions.
  Start agents launches four equal peers from short direct prompts. Use
  `python -m midflight.theater.peers --paused` to start directly in the empty state.
- Existing run files and FalkorDB graphs are retained. The original demo is independent.

This is a semantic view of coordination declarations stored in FalkorDB, not a raw
storage dump or proof of filesystem writes. Local graph/control requests require
the run key; MCP arrivals require a participant token. There is no external CDN or
visualization service at runtime.

Node size encodes declared scope: agents are always the largest circles, with a
small capped increase for the number of distinct files/interfaces their claims
declare. Claims, interfaces, files and directives appear only in inspection details. Size does not indicate
code correctness or agent performance. Agent rings, bold labels and an AGENT mark
keep them recognizable even when an agent has no declarations yet.

## Separate graph experiment

Use a fresh, paused run for the empty-to-connected demonstration, keeping the
existing coding demo and its sessions alive on their original ports:

```sh
python -m midflight.theater.peers --port 8917 --api-port 8918 --paused
```

Open http://127.0.0.1:8917/graph. The canvas starts genuinely empty: no agent sessions
have launched. Start agents launches four real coding sessions. Their circular nodes
appear when their MCP clients register presence; labeled dependency arrows appear
only once provider and consumer claims establish the matching contracts. No existing
state is hidden and replayed as activity. Reset archives this experimental run and
returns it to an empty, paused state. The original demo on port 8907 is independent.

The discarded card monitor at `/vendor/project.html` redirects to the node-based
`/graph` view. It is not embedded into any coding window.
