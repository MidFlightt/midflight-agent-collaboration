# Hosted connector: add one URL, create or join a project

Status: built and tested on branch `hosted-connector`; not yet deployed. Until the
first deployment, the connector URL below is a placeholder.

People use MidFlight by adding a single MCP connector to their coding client and
signing in with GitHub. No clone, no Python, no token files, no tmux. It works from any
computer and any operating system the coding client runs on.

```
https://<HostedUrl>/mcp
```

## What a team does

| Who | Does |
| --- | --- |
| **Lead** | Adds the connector, signs in, and tells their agent “create a MidFlight project called Food app”. The agent replies with a join code like `MF-7KQ2-XW9P`. |
| **Teammate** | Adds the same connector on their own computer, signs in, and tells their agent “join MidFlight project MF-7KQ2-XW9P as payments”. |
| **Every agent** | Calls `join` with its component's agent name, then coordinates with `send`, `check_in` and `objection` exactly as in the local prototype. |

Adding the connector:

| Client | Command |
| --- | --- |
| Claude Code | `claude mcp add --transport http midflight https://<HostedUrl>/mcp` |
| Codex CLI | `codex mcp add midflight --url https://<HostedUrl>/mcp` then `codex mcp login midflight` |
| Claude, ChatGPT | Add a custom connector with the same URL |

The server's landing page (`https://<HostedUrl>/`) shows the same instructions.

## Tools

| Tool | Who | What |
| --- | --- | --- |
| `create_project(name)` | anyone signed in | New project; the caller becomes its lead. Returns the join code. |
| `join_project(join_code)` | anyone signed in | Become a member. Codes are case- and dash-insensitive. |
| `my_projects()` | members | Role, join code, members, agent names (and who runs each), topic owners. |
| `join(name, task, request_id, project_id?, session_id?, dependencies?)` | members | Join as one agent. `project_id` is optional with exactly one project. |
| `send`, `check_in`, `objection` | the agent's member | Unchanged coordination tools, addressed by `session_id`. |
| `assign_owner(project_id, topic, agent)` | lead | Hand a topic to a joined agent; topic subscribers are told. |
| `rotate_join_code(project_id)` | lead | New code; the old one stops working. |
| `remove_member(project_id, login)` | lead | Removes access and frees their agent names for a replacement. |

## Rules that differ from the operator-roster pilot

- **No roster.** Agents declare subscriptions with `join(dependencies=[...])`, as before.
- **First publisher owns a topic.** The first `send(kind="interface")` on a topic nobody
  owns (with `expected_revision=0`) makes that agent the owner. A rejected publication
  claims nothing. Later publications by others are refused; they `objection` or
  message instead. Owners can still `transfer`; the lead can `assign_owner`.
- **Agent names belong to people.** In a project, the first member to join as
  `billing` owns that name. Others are refused and pick another name. One person may
  run several agents (`orders`, `menu`, ...). Sessions are usable only by the member
  who created them.
- **Identity is GitHub sign-in**, through the MCP authorization flow (dynamic client
  registration, PKCE, 1-hour access tokens, 30-day rotating refresh tokens). Codes and
  tokens are stored only as SHA-256 hashes.

Everything else — routing through the dependency graph, policies, objections,
cursors, retries with `request_id` — is the same `Service` the prototype uses.

## Architecture

```
coding client ──HTTPS /mcp + GitHub sign-in──▶ Lambda (hosted connector) ──▶ FalkorDB on EC2
                                                   │                          hosted_registry
                                                   └── NAT ──▶ github.com     hosted_auth
                                                                              hosted_<project>
```

- `midflight/communication/hosted.py`: the MCP server (streamable HTTP, stateless,
  JSON responses), sign-in routes, landing page, `/healthz`, and `create_app_from_env`.
- `midflight/communication/hosted_registry.py`: users, projects, join codes, members,
  agent-name ownership and session ownership in one CAS-protected registry document;
  sign-in records as separate `HAuth` nodes.
- `midflight/communication/memory_store.py`: in-memory store for tests and local runs.
- Sign-in reuses `midflight/api/oauth.py` (the original hosted connector's GitHub flow).
- Deployed as a second Lambda in the `midflight-shared-communication` stack, from the
  same archive. The token RPC function, its URL, pilot credentials and invites are
  unchanged. The connector runs in a private subnet behind a NAT gateway because GitHub
  sign-in needs the internet; only it and the RPC Lambda can reach the database.

## Run it locally

```sh
uv sync --locked --extra falkordb
MIDFLIGHT_PUBLIC_URL=http://127.0.0.1:8000 MIDFLIGHT_DEV_LOGIN=1 MIDFLIGHT_HOSTED_STORE=memory \
  uv run uvicorn midflight.communication.hosted:create_app_from_env --factory --port 8000
claude mcp add --transport http midflight-local http://127.0.0.1:8000/mcp
```

The dev login replaces GitHub with a form where you type any login, so two terminals
can sign in as two people. Memory storage resets when the server stops. Use
`MIDFLIGHT_HOSTED_STORE=falkordb` with `MIDFLIGHT_DB_HOST`/`MIDFLIGHT_DB_PORT` for
persistent local storage (`docker compose -f compose.graph-hacks.yml up -d`).

## Deploy

1. **GitHub sign-in.** Use the existing MidFlightt GitHub App (add a callback URL) or
   create an OAuth App. The callback URL is `https://<HostedUrl>/oauth/github/callback`,
   known after step 2. Save `{"client_id": "...", "client_secret": "..."}` in a private
   file outside Git.
2. **First deployment** creates the connector's Function URL (and the NAT gateway):

   ```sh
   uv run --extra falkordb python infra/shared/package.py
   uv run --extra falkordb python infra/shared/deploy.py --profile midflight-dev \
     --config "$HOME/.midflight-shared/teammate-pilot/config.json"
   uv run --extra falkordb python infra/shared/deploy.py --profile midflight-dev --execute CHANGE_SET_ID
   ```

   Review the change set first: it should add the hosted resources and update the
   database security group in place, with no database or volume replacement.
3. **Second deployment** passes the now-known URL and the GitHub credentials:

   ```sh
   uv run --extra falkordb python infra/shared/deploy.py --profile midflight-dev \
     --config "$HOME/.midflight-shared/teammate-pilot/config.json" \
     --github-oauth /private/path/github-oauth.json
   ```

   Later deployments keep both without the flag.
4. **Check** `https://<HostedUrl>/healthz` returns `{"status":"ok"}` (not
   `"configured": false`), open the landing page, then add the connector in a client
   and create a project.

## Tests and limits

- `tests/unit/test_hosted_connector.py`: tool surface, two people sharing a project,
  name and session ownership, first-publisher ownership, routing, lead tools, removal.
- `tests/integration/test_hosted_connector_http.py`: the real server over HTTP with the
  OAuth flow (register, authorize, dev sign-in, token, refresh) and two signed-in people.
- `tests/integration/test_hosted_connector_falkordb.py` (`--falkordb`): persistence
  across a restart in real FalkorDB.
- The registry is one JSON document read on every call; fine for many teams, not for
  very large numbers of projects. No per-user rate limits or project caps.
- The hosted connector has not yet been deployed or tried from a real coding client.
