# GH-05: equal-peer collaboration experiment

Branch: `GH-05-peer-collaboration`, based on `GH-04-four-agent-demo`.
The existing scripted demo stays on its own branch and port 8897.

Run separately:

```sh
uv sync --locked --extra falkordb --extra demo
uv run --extra falkordb --extra demo python -m midflight.theater.peers
```

Open http://127.0.0.1:8907 (API 8908), or use `--port 8909 --api-port 8910`.
Each composer is prefilled, unsent, with a direct request:

- Pricing: “Add volume discounts.”
- Checkout: “Add promo codes.”
- Reporting: “Add a revenue summary.”
- Notifications: “Add signup confirmations.”

Workspaces start from the small Python shop application, with an HTTP router,
module interfaces, baseline tests and README. Each agent owns its module and tests. Pricing and Checkout deliberately start with
different proposed public return shapes for get_promo_codes(): a dictionary on the
Pricing branch and a list on the Checkout branch. These are explicit prototype
interfaces, not product requirements or injected agent claims. The promo catalog defines SAVE10 as 10% off,
so a basic prompt does not require the agent to invent a coupon.
Requirements are seeded into plan v1; agents do not need to republish these assignments.
The prompts contain no coordination choreography. AGENTS.md and MCP supply the protocol.

After the initial work, type this direction in any window:

> Include a price expiry time, and reject checkout when the quote has expired.

The intended model adds expires_at to the price quote and validates it in checkout.
The order contract retains total_cents, so reporting and notifications are unaffected.
The direction is interpreted by the agent, not a keyword handler. Tests verify the
actual dependency routing for that model. If an agent also changes order fields, that
can legitimately expand the affected set. Read the proposed plan rather than forcing
an affected-agent list. There is no scripted rejection: compatible claims are approved.
Finished agents wait for their next human work request; there are no idle wake-ups.

The starter's integration path is quote → create_order → revenue, with signup messages
independent. Baseline tests cover starter behavior; agents must implement and test the
requested features. The experiment does not install itself into arbitrary repositories.

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

Agents discover changes at task checkpoints. The harness never sends automatic
checkpoint prompts or starts an idle agent turn. Outstanding directives remain queued
until the agent next checks in, including when the human next gives it work.
Sessions persist between stages; Reset starts a fresh isolated project with the same
peer capabilities and preserves earlier run files.

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

## Source activity observer

The earlier agent-only graph is a semantic projection of claims. Its readable edge
sentences were viewer-authored descriptions, not source-code facts. It does not
observe file writes. For an actual filesystem view attached to the same coding run:

```sh
python -m midflight.theater.source_view --upstream http://127.0.0.1:8907 --port 8927
```

Open http://127.0.0.1:8927/ alongside the coding view at http://127.0.0.1:8907/.
The observer proxies read-only coordination snapshots and locates that project's
local run directory from its saved report. It follows upstream Reset to the new
run automatically; it exposes no reset, plan-publishing or agent-start endpoints.
Existing sessions and prompts are unchanged.

- Large circles are actual connected agent identities from FalkorDB coordination data.
- Small file nodes come from eligible files found in each agent workspace, with solid
  ownership connections. A filename in a claim alone cannot create a file node.
- Dashed arrows represent matching provided/consumed contracts from claims. Labels
  use exact contract/field identifiers, such as `price.total_cents`. They are not an
  import graph or independently verified dependencies extracted from the source code.
- File metadata includes SHA-256, size and mtime. One-second snapshots detect newly
  observed files, content changes and removals. Existing files establish the baseline;
  attaching the viewer does not replay them as newly created. Toasts and short rings
  mark later observed changes. The view cannot attribute a write to a particular
  process: a file is associated with the workspace containing it, not proven authorship.
- A new workspace also establishes a baseline before generating change notifications.
  Read failures retain prior observations as unavailable rather than inventing deletions.
- Scanning excludes the seeded TASK.md, hidden paths, symlinks, dependency/build/cache
  folders, and unsupported extensions. Limits are 300 eligible files per workspace
  and 2 MB per hashed file; incomplete observation is surfaced in the status line.
- File events are an in-memory, bounded observer log, not a durable audit trail.
  Changes entirely between polls can be missed; renames look like removal/addition.

This filesystem observer is new local demo tooling. Production MidFlight currently
coordinates declared scope and contracts; these observations are not automatically
stored in FalkorDB, nor do they establish a deployed code-indexing feature.

For the default local setup, the demo's existing `/graph` link on port 8907 now
opens the file observer at port 8927. The old agent-only view remains accessible
as `http://127.0.0.1:8907/graph?legacy=1`; the isolated 8917 experiment is unchanged.
The observer must be running for this local shortcut to work.

## Manual start

Startup and Reset create a fresh isolated project and four connected sessions. Each
composer contains an editable task prompt, but no task is submitted automatically.
Press Enter in each pane when ready, or edit the prompt first. Reset archives the
previous run files and replaces the active graph, claims, directives and workspaces.

## Checkpoint policy

The workspace and MCP instructions share one policy. The normal path is one startup
check-in, claim approval, implementation and tests, then one completion check-in.
Approval covers using the declared interfaces; no separate check is required immediately
after approval or directive acknowledgement. Additional checks remain appropriate for
pending review, changed assumptions or scope, and relevant dependency updates. Two is
a normal-case target, not a hard limit. Initial human requests may still add genuinely
missing requirements; requests already represented in the plan should not republish it.
There are no automatic idle wake-ups. Each new work request starts with a check-in
that discovers outstanding relevant directives.

Live discount-prompt experiments and their actual outcomes: [trial results](discount-prompt-trials.md).

## Semantic interface rehearsal

The peer launcher now injects the hosted AI reviewer and conservative public-interface
policy adapted from the local PigeonPost demo. The original harness and production
reviewer configuration retain their defaults. Reviewer transport uses the installed
Codex CLI with saved sign-in, ephemeral read-only execution in a temporary directory,
structured output and no inherited project MCP configuration. It uses account model
capacity. An unavailable reviewer does not become a successful review.

Start Pricing first with “Add volume discounts.” Once its claim is APPROVED, start
Checkout with “Add promo codes.” No bad claim or verdict is injected. Agents declare
what their local prototypes provide or consume, and may notice and fix the drift early.
A rejection is an observed outcome, not a guaranteed output for every autonomous run.

Only approved peer assumptions can guide another task. Technical corrections preserve
earlier approved claims while asking a later incompatible claimant to adapt. This is
an isolated demo coordination policy, not a change to the core domain service.
Semantic review uses a second contradiction check and a technical/product ruling.
It distinguishes public output from private storage and accepts an explicit conversion.

A live control review rejected an explicit dictionary/list conflict and accepted a
private dictionary converted to the required public list. The first full real-agent
rehearsal approved Pricing, returned NEEDS_REVISION with semantic_mismatch for Checkout,
and approved Checkout's corrected mapping-based claim. There was an intermediate DRAFT
because a partial claim revision omitted fields; peer instructions now require complete
revision submissions to match the local endpoint's behavior. Pricing stayed approved.
Both agents used two check-ins. Independently combined generated modules passed the
actual catalog → discounted quote → promo checkout integration.

Artifacts and timing for fresh interface trials are retained locally under
~/.local/share/midflight-demo/interface-trials/. These are actual agent sessions, unlike
PigeonPost's historical recorded-claim backend replay results. See interface-trials.md
for all completed attempts, including unsuccessful ones.
