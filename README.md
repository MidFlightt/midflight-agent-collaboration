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
raises objections, like the agents in the demo below.
[Full connection guide and troubleshooting](https://github.com/MidFlightt/midflight-agent-collaboration/blob/hosted-connector/README.md#use-midflight-connect-your-coding-agent).
The connector's code is on the
[`hosted-connector`](https://github.com/MidFlightt/midflight-agent-collaboration/tree/hosted-connector)
branch.

