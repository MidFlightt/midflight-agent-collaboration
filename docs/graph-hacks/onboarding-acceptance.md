# GH-07 development acceptance

This is development validation, not a clean merged-release signoff. Core implementation
commit: `d10711e`; setup guide commit: `74f343e`. The final README/CI documentation edits
were still in progress during the real-client replay. No production repository was edited.

## Deterministic checks

- `pytest --falkordb -o addopts='' -q`: **542 passed**, including isolated real Docker
  FalkorDB tests. No model calls occur in this suite.
- `ruff check .`, `ruff format --check .`, `git diff --check`: passed.
- `uv build`: source distribution and wheel built successfully. Installed the wheel
  with its FalkorDB extra into a separate environment; its CLI authenticated and
  recovered plan v2 from the running service.
- New tests cover unauthorized bootstrap, retry with the same identity, conflicting
  identities, revoked identities, absence of bootstrap from normal server entry points,
  private file permissions, preserving existing repo instructions, local-only URLs,
  lead-only plan writes, MCP tool discovery and general plan proposal/approval.
- The new graph integration test creates a bookings project, approves its plan, opens a
  fresh adapter, authenticates the original identity and checks a contract update reaches
  dependent tasks. CI includes this test in the real-database job.

## Real repository and coding client

Created a separate Git repository for seat reservations and initialized it with
`midflight init`, using `backend` and `emails` identities plus the lead. This did not
use `theater.seed`, generated TASK.md files, a subscription-specific handler, or demo
checkpoint injection. A separate local service used its own FalkorDB graph.

The **actual stdio MCP transport** successfully handled `project_context`,
`propose_plan`, `get_plan` and `approve_plan` for a general bookings specification.
The acceptance operator supplied/reviewed this structured plan; this step did not test
an LLM independently generating a plan from a natural-language product brief.

A real Codex session then received only this ordinary development request:

> Implement your assigned seat reservation task and run its tests. Do not commit or push.

With the installed AGENTS.md section, it called `project_context`, `check_in`,
`submit_claim` and subsequent check-ins, implemented `reserve()` and produced four
passing tests. A separate `python -I -m unittest discover` invocation confirmed them.

The operator approved plan v2, adding `seat_number: integer` to the booking contract
and corresponding acceptance criteria. The local service was stopped and restarted
against the same graph and private home. The original credentials authenticated;
plan v2, claim state `needs_revision`, and its pending directive survived the restart.

A **fresh** coding session, without the old conversation, received:

> Continue your assigned task against the current approved plan and run its tests.
> Do not commit or push.

It discovered the change, acknowledged it, revised claim C-1 to revision 2 and updated
`reserve()` to return the requested seat number. Five tests passed independently.
Final API readback showed plan v2, approved claim revision 2, and no push blockers.
Both coding runs left commits/pushes to the human.

The optional `--approve-coordination-tools` flag was used explicitly for these
headless tests. It preapproves only this session's local context/claim/check-in/ack tools;
plan proposal and approval are excluded. The initial test without that flag was
correctly blocked by the client's inherited headless approval policy. Global Codex
configuration and unrelated MCP connections were not modified.

This validates one real coding identity across a service restart and a new conversation.
It does not claim an end-to-end multi-agent implementation of the entire bookings app,
a newly validated public hosting deployment, or a fresh physical-machine installation.
The existing isolated multi-agent/graph suites cover the other coordination paths.

The original four-pane presentation service and sessions were left untouched.
