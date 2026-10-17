# Midflight — current team plan

Updated October 16, 2026 (America/Los_Angeles).

This is the current execution plan for the Graph Hacks work: what exists, what
remains, and who owns each deliverable. Use it alongside the detailed
[Graph Hacks development plan](docs/graph-hacks/development-plan.md).
The older [development plan](docs/development-plan.md) describes the earlier
hosted-service effort; its dates and assignments are not the current team schedule.
This document does not make proposed product behavior an implemented feature.

## Goal

Multiple coding agents work on connected tasks. When a requirement or interface
changes, Midflight identifies which tasks may be affected, explains the dependency
paths, and delivers relevant updates at agent check-ins. Unaffected agents continue.

Our delivery needs three things: working coordination, a setup another developer
can reproduce, and a clear recorded demonstration of what actually works.

## Current status

| Area | Status | Evidence and limits |
| --- | --- | --- |
| Core coordination | Implemented | Claims, shared plans, review, decisions, escalations, directives, check-ins, and separate implementation verification exist. |
| FalkorDB persistence and recovery | Merged | Store adapter and recoverable worker are on `main`; see [runtime and recovery](docs/graph-hacks/runtime-worker.md). |
| Dependency analysis and propagation | Merged | Task/contract graph, direct and downstream impact, explanatory paths, and delivery through directives/check-ins are on `main`. [PR #5](https://github.com/MidFlightt/midflight-agent-collaboration/pull/5) and [PR #6](https://github.com/MidFlightt/midflight-agent-collaboration/pull/6) are merged. |
| Original four-agent demo | Merged | Real coding sessions, a human-entered subscription direction, reset, and independent acceptance evidence. The original change handler is scenario-specific. |
| Repository onboarding | Built; review and independent testing pending | [PR #7](https://github.com/MidFlightt/midflight-agent-collaboration/pull/7) is open with both CI checks passing at this update. Adds `midflight serve`, `midflight init`, `midflight agent`, and reusable instructions. A separate bookings app was tested; this is not yet an independent fresh-user validation. |
| Peer-agent experiment | Experimental branch | [GH-05-peer-collaboration](https://github.com/MidFlightt/midflight-agent-collaboration/tree/GH-05-peer-collaboration) uses short prompts and accepts direction through any agent window. Prior rehearsal passed an EUR-pricing change. This does not establish that the unified claim workflow below is implemented. |
| Live graph visualization | Built on experimental branch; presentation still evolving | Reads FalkorDB-backed agent/claim/interface declarations. Layout and dependency explanations are being simplified. It is a view of coordination state, not an automatic map of every source-code dependency or raw database node. |
| Unified claim workflow | Design reviewed; implementation pending | Ordinary claims currently validate work against accepted contracts. Shared changes and graph propagation still use the separate plan-change path on `main`. |
| Pitch and submission video | Assets available; final assembly pending | Existing 2:10 Remotion pitch, editable source, FalkorDB slide, and dependency animations are in Frederik's local submission workspace. The existing pitch has a demo placeholder and predates the new FalkorDB material. Final recording, integration, export, and publishing remain. |

The local demo addresses are `http://127.0.0.1:8897/` (original) and
`http://127.0.0.1:8907/` (peer experiment), with `/graph` on the peer demo.
These are local development addresses, not public deployments or guaranteed running
services. See [demo documentation](docs/graph-hacks/four-agent-demo.md) for startup;
experimental behavior must be checked against its branch.

## Ownership and remaining work

Only the owners below are assigned. **Unassigned** work is available for someone to
pick up. Before starting, record an owner and branch/PR here so work does not overlap.

| ID | Deliverable | Owner | Remaining work / done when |
| --- | --- | --- | --- |
| TEAM-01 | Product direction and acceptance decisions | Frederik | Settle the unified workflow's acceptance, response, and escalation policies. Record the agreed behavior before core implementation begins. |
| TEAM-02 | Live demo and visualization | Frederik | Finish a readable view of agents and their dependencies; rehearse a change from a clean start; ensure change/delivery cues match saved state; show unaffected work continuing. Select the branch/version to record. |
| TEAM-03 | Pitch and submission video | Frederik | Integrate the FalkorDB explanation and final demo recording into Remotion, replace the placeholder, review the narrative against implemented behavior, render the final MP4, and publish the submission assets. |
| TEAM-04 | Fresh-repository setup and usability | Mithilesh | Independently test PR #7 from a clean checkout and fresh application repo, connect multiple agents with ordinary prompts, introduce a change, restart/reconnect, fix setup problems, and produce instructions another developer can follow without live help. |
| TEAM-05 | Unified workflow architecture | Unassigned | Inspect current flows; document implemented versus missing behavior; define proposal acceptance, affected-agent responses, concurrency, and technical versus product authority; deliver a workflow diagram and the smallest coherent implementation plan for TEAM-01 decisions. |
| TEAM-06 | Unified claim implementation | Unassigned | After TEAM-01 and TEAM-05, implement the agreed claim-driven shared-change path, reusing review, graph impact, decisions, and check-ins. Include behavior tests and preserve separate commit verification. |
| TEAM-07 | Independent coordination correctness tests | Unassigned | Build repeatable tests for direct/downstream impact, unaffected tasks, conflicting and stale proposals, reconnect/restart, and duplicate requests. Record failures and add fixes or issues. Verify application output independently of claim approval. |
| TEAM-08 | Branch integration and final rehearsal | Unassigned | Review onboarding and experimental changes, open/review PRs, resolve integration issues, and run a clean end-to-end rehearsal on the exact combined commit selected for recording. Preserve existing runs and evidence. |
| TEAM-09 | Submission completeness | Unassigned | Check the actual submission requirements, repository access, setup instructions, graph-model/query documentation, video link, and stated limitations. Confirm an outsider can find and run the submitted version. |

## Mithilesh's setup acceptance checklist — TEAM-04

- [ ] Start from a clean checkout and record prerequisites, OS, branch, and commit.
- [ ] Review/test PR #7 explicitly; do not assume its commands are already on `main`.
- [ ] Start FalkorDB and the service using only the documented instructions.
- [ ] Connect a fresh application repository with no commerce-demo seed.
- [ ] Launch multiple separately identified agents and give ordinary development prompts.
- [ ] Establish the application's actual tasks, requirements, and interfaces.
- [ ] Introduce a change; verify relevant agents discover and address updates.
- [ ] Restart the service, reconnect an agent, and verify persistence and pending updates.
- [ ] Run the application's tests independently and save reproduction steps/results.
- [ ] Fix missing steps, confusing errors, and undocumented assumptions in setup/docs.
- [ ] Have another person follow the walkthrough without assistance; record any gaps.

## Core workflow to design, then implement — TEAM-05 / TEAM-06

The intended entry point is one claim workflow:

1. Any agent submits or revises a claim describing its intended work, assumptions,
   interfaces, and any proposed shared changes.
2. Midflight reviews the proposal against accepted context and other claims.
3. FalkorDB dependency analysis identifies direct and downstream impact with paths.
4. Midflight coordinates technical consequences; product decisions go to the lead.
5. Once the agreed acceptance conditions are satisfied, the shared context is updated.
6. Affected agents receive scoped updates at check-ins and respond or revise their
   claims. Unaffected agents continue.
7. Actual commits and application behavior are verified separately.

This is a target workflow, not a description of the complete current implementation.
Versioned plans can remain the internal record of accepted context.

Decisions required before implementation:

- When exactly does a proposal become accepted shared context?
- Which technical changes may be accepted without a product decision?
- Which affected owners must respond before acceptance, especially for breaking changes?
- How are conflicting/concurrent proposals and stale baselines handled?
- What may agents continue doing while a proposal is pending?
- What happens when semantic review or impact evidence is unavailable?

Do not equate proposal submission, a favorable review, directive acknowledgement,
or silence with acceptance of a shared change. The response policy is still to be
agreed. Keep unaffected work moving while dependent work waits for required decisions.

## Shared acceptance scenario

Use a change to **only the price contract** to establish genuine dependency selection:

```text
Pricing -> price contract -> Checkout -> order contract -> Reporting

Notifications: no relevant dependency
```

Required evidence:

- Checkout is identified directly and Reporting through its downstream dependency.
- Stored dependency paths explain the selection; all affected tasks were not merely
  listed explicitly in a scenario handler.
- Relevant agents receive updates through check-ins and adapt their implementations.
- Notifications receives no unrelated directive and its implementation stays valid.
- Independent application tests establish correct integrated behavior.
- On the new workflow, the change originates from an ordinary claim, not a
  subscription-specific direction handler. Until implemented, test the current
  plan-change path and label that result accurately.

Add failure cases for stale proposals, conflicting changes, duplicate submissions,
and an agent reconnecting after missing an update. Save the tested commit and
reproduction commands with the results.

## Order of work

1. **Now, in parallel:** TEAM-04 fresh setup validation, TEAM-05 architecture review,
   TEAM-07 tests of existing behavior, and TEAM-02 demo/visualization refinement.
2. **Agree the core policy:** TEAM-01 resolves the decisions from TEAM-05.
3. **Implement and integrate:** TEAM-06 delivers the agreed workflow; TEAM-08 combines
   reviewed changes and repeats acceptance checks against the selected commit.
4. **Record and submit:** TEAM-03 records the verified behavior and assembles the
   video; TEAM-09 checks the final submission. Video preparation can proceed earlier,
   but final claims and footage must match the version actually submitted.

If the unified workflow will not be ready for the submission, explicitly choose and
document the implemented scope. Keep the existing plan-change demonstration available
and explain its limits; do not present the proposed workflow as completed.

## Evidence and handoffs

- Use a branch and PR for each scoped change. Link it beside the task when available.
- Keep merged, experimental, proposed, and verified behavior distinct in status updates.
- Treat earlier successful tests as evidence for their tested commit, not every later branch.
- For cross-task interfaces, agree the change before building against it.
- Update this file as owners volunteer, decisions are settled, and deliverables land.
- Local video assets currently live in
  `/Users/frederikjonsson/Documents/ChatGPT/Graph-hacks/Midflight-video-submission/`.
  They are not automatically available to teammates: arrange a shared source/export
  handoff and add the link here before someone else takes video work.

## References

- [Graph Hacks development plan](docs/graph-hacks/development-plan.md)
- [Task/contract dependency graph](docs/graph-hacks/dependency-graph.md)
- [Graph propagation](docs/graph-hacks/graph-propagation.md)
- [Runtime and recovery](docs/graph-hacks/runtime-worker.md)
- [Four-agent demo](docs/graph-hacks/four-agent-demo.md)
- [Repository onboarding PR #7](https://github.com/MidFlightt/midflight-agent-collaboration/pull/7)
- [Peer demo / live graph branch](https://github.com/MidFlightt/midflight-agent-collaboration/tree/GH-05-peer-collaboration)
