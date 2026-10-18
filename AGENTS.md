# MidFlight agent communication prototype

This collaboration repository's current hackathon entrypoint is
`python -m midflight.communication.harness` (also `midflight.theater.peers`).
Read [architecture and measured validation](docs/agent-communication.md).

- The four coordination tools are `join`, `send`, `check_in`, `agree`.
- Coding agents interpret human directions and negotiate interfaces. MidFlight makes no model calls.
- No claim, mandatory reviewer, approval or revision gate belongs in this runtime.
- Owners publish versioned interfaces; consumers follow them without mutual acceptance.
- Keep changing business rules in policy messages, separate from API shape and calling conventions.
- Explicit objections persist until their author resolves them; publication does not close them.
- Agreement is optional participant intent about a proposal revision, never proof of implementation.
- Dependencies are explicit topic edges. Policy messages and replies cannot expand beyond affected agents.
- Keep coding sessions real, task prompts short and check-ins tied to work. Never poll idle agents.
- Reset archives code and coordination, creates a fresh graph, and prepares unsent prompts.
- Preserve existing work. Legacy claim/reviewer modules remain as historical experiments;
  do not silently migrate their graphs into the communication schema.
- Changes belong only in `MidFlightt/midflight-agent-collaboration`; leave the official repository alone.
- Use retry IDs, atomic version guards and independent durable session cursors.
- Test implementation with actual combined code. Never substitute agent reports for tests.
- Do not commit run credentials, profiles or raw session logs. `runs/` is ignored.

Checks: `uv sync --locked --extra falkordb --extra demo`, `uv run ruff check .`,
`uv run pytest`, and `uv run --extra falkordb pytest --falkordb` for isolated real-database tests.
The historical repository guidance is retained in `docs/archive/agent-guide-before-communication.md`.
Its claims/reviewer workflow does not apply to this migration.
