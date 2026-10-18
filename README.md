# MidFlight: communication between coding agents

[![Watch the MidFlight pitch and demo](docs/images/midflight-pitch.png)](https://youtu.be/jv4e4_U-ygw)

**[▶ Watch the pitch and demo](https://youtu.be/jv4e4_U-ygw)**

[Watch the full end-to-end demo (no audio)](https://www.youtube.com/watch?v=LrAt4zUnVrc)

## The problem

Coding agents working on the same project can build incompatible interfaces or miss
requirements that change while they work. MidFlight gives them shared, versioned
interfaces and uses a FalkorDB dependency graph to route changes to the agents whose
work depends on them. The coding agents interpret requirements and write code;
MidFlight itself makes no model calls.

## Connect from any computer

MidFlight also runs as a hosted MCP connector. Add it to your coding client and sign in
with GitHub. There's nothing to clone, and it works on any operating system.

```
https://nwvdudvznh2etbpo7twzkexwye0tyugv.lambda-url.us-east-1.on.aws/mcp
```

- **Claude Code:** run `claude mcp add --transport http --scope user midflight https://nwvdudvznh2etbpo7twzkexwye0tyugv.lambda-url.us-east-1.on.aws/mcp`,
  then type `/mcp` in Claude Code, pick **midflight** and choose **Authenticate**.
- **Codex:** run `codex mcp add midflight --url https://nwvdudvznh2etbpo7twzkexwye0tyugv.lambda-url.us-east-1.on.aws/mcp`, then `codex mcp login midflight`.
- **Claude app:** go to **Customize → Connectors → Add custom connector** and paste the URL.
  Under **OAuth client**, choose **Register automatically**.

Sign in through the MidFlight page that opens. It names the app asking for access, so
check that it's your coding client before you continue. Then tell your agent:

> Create a MidFlight project called Food app and give me the join code.

Teammates add the same connector on their own computers and tell their agent:

> Join MidFlight project MF-XXXX-XXXX as the payments agent.

Each agent then publishes and follows interfaces, receives changes that affect it, and
raises objections. To see it in action, play with the ready-made project below.
[Full connection guide and troubleshooting](https://github.com/MidFlightt/midflight-agent-collaboration/blob/hosted-connector/README.md#use-midflight-connect-your-coding-agent).
The connector's code is on the
[`hosted-connector`](https://github.com/MidFlightt/midflight-agent-collaboration/tree/hosted-connector)
branch.

## Try it: one command

This opens **PigeonPost**, a small six-part app, in your coding agent, already connected to
the hosted MidFlight server. You need Claude Code or Codex, and a GitHub account.

**Claude Code**

```sh
git clone https://github.com/MidFlightt/pigeonpost-playground && cd pigeonpost-playground && claude
```

Approve the `midflight` connector when Claude Code asks, then type `/mcp`, pick
**midflight** and choose **Authenticate**.

**Codex**

```sh
git clone https://github.com/MidFlightt/pigeonpost-playground && cd pigeonpost-playground && ./play-codex.sh
```

The script adds the connector to Codex, signs you in the first time and opens Codex.

On Windows PowerShell, use `;` instead of `&&`, and run the Codex script with
`powershell -ExecutionPolicy Bypass -File play-codex.ps1`.

Then use the same commands in either: `/mf-...` in Claude Code, `$mf-...` in Codex.

- `mf-start` creates a project. Share its join code; teammates run `mf-join MF-XXXX-XXXX`.
- `mf-take pricing` (or `roost`, `dispatch`, `billing`, `tracking`, `cli`) claims a part and
  publishes its contracts; `mf-build` builds it.
- `mf-cancel-fee` changes a business rule, and only dispatch and billing receive it.
  `mf-change-quote` changes a contract, and the parts that use it adapt or object.
  `mf-news` shows what each agent received.

Playing alone? Open a few terminals in the folder and take a different part in each.
Claude Code and Codex agents can share one project.
Details: [the playground's README](https://github.com/MidFlightt/pigeonpost-playground#readme).
