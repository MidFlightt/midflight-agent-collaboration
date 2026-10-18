# Connect your coding agent to the shared MidFlight pilot

For trying the demo independently, use the [invite setup flow](invite-setup.md).
Each visitor gets an isolated project automatically. The instructions below remain
for collaborators deliberately joining the existing shared teammate pilot.

The shared backend stores coordination; your code and coding session stay on your
computer. You need Git, uv, Python 3.12+ (uv can install it), and your coding client.
You do **not** need AWS credentials, Docker, tmux, or a local database.

## 1. Install the bridge

```sh
git clone --branch codex/shared-backend https://github.com/MidFlightt/midflight-agent-collaboration.git
cd midflight-agent-collaboration
uv sync --locked --extra falkordb
```

The FalkorDB extra currently supplies imports used by the shared bridge; you do not
run a database locally. If you already have the local demo, use a separate clone
so switching branches cannot disturb your recording/session.

## 2. Get your private agent credential

Ask Frederik for your assigned agent name and its individual token file. Available
pilot identities are `billing`, `delivery`, `booking`, and `notifications`, in the
same `teammate-pilot` project. Do not share all four credentials or commit a token.

For example, place your file at `~/.midflight/billing.token` and restrict its permissions:

```sh
mkdir -p "$HOME/.midflight"
chmod 700 "$HOME/.midflight"
chmod 600 "$HOME/.midflight/billing.token"
```

These commands assume you have already saved the supplied file at that path.
The token binds both project and agent; entering another name does not change identity.

## 3. Add the four tools to Codex

Run from the cloned repository, replacing `billing.token` with your assigned file:

```sh
codex mcp add midflight \
  --env MIDFLIGHT_URL=https://iimfbygoctyel62ztqcitecoxy0ykppp.lambda-url.us-east-1.on.aws \
  --env MIDFLIGHT_TOKEN_FILE="$HOME/.midflight/billing.token" \
  -- "$PWD/.venv/bin/python" -m midflight.communication.mcp
codex mcp get midflight
```

If you already have an MCP entry called `midflight`, save its configuration before
replacing it. Existing local demo sessions use their own isolated profiles and are
not changed by this command. On Windows, use your Python executable's actual path
(e.g. `.venv/Scripts/python.exe`) and your private token file's absolute path; that
client platform has not been verified in this pilot.

Start a new coding session in **your working repository**, not the MidFlight bridge
checkout. The tools should be `midflight.join`, `midflight.send`,
`midflight.check_in`, and `midflight.object`. This uses a local stdio bridge;
the AWS URL is an authenticated RPC API, not a directly connectable HTTP MCP URL.
Do not register it with `codex mcp add --url`.

The CLI setup syntax was checked against the installed CLI and
[official OpenAI documentation](https://developers.openai.com/codex/mcp).
For other MCP clients, use the same executable/arguments/environment in their stdio
server configuration; those clients have not been tested here.

## 4. Start useful work

Give your agent its real task and assigned name, for example:

> Implement billing and revenue reporting. Join MidFlight as billing and use relevant
> published interfaces. Keep coordination tied to useful work checkpoints.

The example roster has Delivery owning `delivery-record`, Booking owning
`booking-request`, and Notifications owning `confirmation`. Billing and Delivery
subscribe to `cancellation-policy`; Booking and Notifications do not. Consumers may
adapt directly to a compatible published interface. A genuine incompatibility can
be recorded against an exact revision with `object`; only its author resolves it.

Your agents exchange context, not files. Use Git to share actual implementations
and explicitly run integration tests against the combined code. A delivered message
is not proof of reading or application. Idle agents intentionally remain idle until
a useful task resumes; no repeated nudges or polling are needed.

## Check the connection

```sh
curl --fail https://iimfbygoctyel62ztqcitecoxy0ykppp.lambda-url.us-east-1.on.aws/healthz
```

Expect `{"status":"ok"}`. This checks the service, not your credential. A successful
`join` from your coding session verifies your token and agent binding. If you get
401, check the token file and endpoint; 403 usually means the wrong agent/session.
Retry an uncertain write with the same request ID and identical input. If a response
was lost, replay from your last received cursor rather than assuming it was applied.

The local four-panel demo remains separately available on `codex/agent-communication`.
Its Reset does not reset this shared pilot. For an unrelated team/project or more
agent identities, ask the operator to provision separate credentials and ownership.
