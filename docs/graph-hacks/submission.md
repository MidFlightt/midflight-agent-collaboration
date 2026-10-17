# Graph Hacks submission readiness

Intended track: **Agent Memory and Coordination** — persistent shared context,
versioned plans/claims, graph-selected handoffs and durable recovery.
[Official tracks](https://www.wemakedevs.org/hackathons/falkordb#tracks).

| Required item | Location / status |
| --- | --- |
| Public source repository | https://github.com/MidFlightt/midflight-agent-collaboration |
| Setup instructions | Root README and [repository setup](repository-setup.md) |
| Graph data model | README diagram and [dependency graph](dependency-graph.md) |
| Cypher / algorithms | [Queries](queries.md), linked executable source and tests |
| Working local deployment | `uv run --extra falkordb midflight serve`, with pinned persistent FalkorDB Compose service |
| Demo video | **Still required: record, publish and add the final URL here and in README.** |
| Entered track | Agent Memory and Coordination; select it in the actual submission form |

A public hosted deployment is not claimed. The submission uses complete local setup;
this must be accompanied by a working demo video. No submission form is sent by this PR.

## Video outline

1. Show the public repository and the quickstart commands.
2. Initialize a separate, ordinary repository. Show preserved instructions and installed
   MidFlight integration, without displaying any credentials.
3. Ask the lead for a real application plan; review and approve it. Show Task/Contract/
   Requirement nodes and a dependency path in FalkorDB.
4. Start agents on their assigned tasks using ordinary coding requests. Show claims,
   check-ins and independently passing application tests.
5. Change a product requirement through the lead; approve the new plan. Show relevant
   agents discovering directives and the unrelated agent receiving none. Explain the
   graph path behind the choice; don't broadcast the new direction to all agents.
6. Restart the service and demonstrate that the plan, claims and pending work persist.
7. Finish with integration tests. The colored terminal view is optional presentation;
   colors are not independent evidence of correctness.

## Final manual acceptance

Run the README from a clean checkout on a machine without this developer's private
Codex profiles or demo workspace. Exercise a second application, including unsupported
or ambiguous requirements: the lead must propose a plan instead of matching a phrase.
Confirm that no tokens appear in Git, screenshots or recordings. Record the commit SHA,
the commands actually used and test output; don't label a dirty rehearsal as a merged
release test. Add the video URL and confirm repository visibility before submitting.
