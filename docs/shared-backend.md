# Shared coordination backend

Status: implemented and tested locally across independent HTTPS/MCP processes.
**Not yet deployed to AWS.** Deployment in account 825125930394 is blocked because
`midflight-dev` lacks EC2 and CloudFormation permissions. There is no teammate URL yet.
The recorded four-panel local prototype remains on `codex/agent-communication`.
Shared-backend development is on `codex/shared-backend`.

## Architecture

Each teammate runs a local stdio MCP bridge exposing exactly `join`, `send`,
`check_in`, and `object`. The bridge calls the shared HTTPS API. Coding agents,
repositories, and model credentials remain on their computers. No source files
are uploaded by this bridge; agents' coordination messages are stored remotely.
Teammates share code through Git, as usual. This does not merge work or run tests
on their behalf, nor does it provide a combined remote four-panel terminal viewer.

One bearer credential identifies one project and agent on the server. Supplying
another agent name, session, or project cannot change that identity. Only a session
belonging to that identity can be read or used to publish, transfer ownership, or
resolve its own objections. Multiple sessions of one agent retain independent cursors.
A shared agent credential intentionally grants access to all that agent's sessions;
issue separate agent identities when people need separate access boundaries.

The HTTP wrapper uses the existing FalkorDB CAS transactions, receipts, routing and
exact revisions. No acceptance/reviewer gate is added. Updates arrive only through
useful tool calls; the server never wakes peers. A connection failure may occur after
commit: retry the same write with the same request ID and input. `check_in(after=...)`
can replay a lost response. Never infer reading or application from HTTP delivery.

## AWS deployment without a custom domain

The separate `midflight-shared-communication` stack uses:

- Lambda with an AWS-provided Function URL (HTTPS), checking bearer credentials.
- One ARM EC2 `t4g.small` running the pinned FalkorDB image.
- A separate encrypted 20 GiB EBS data volume with AOF fsync on every write.
- A new VPC and security groups: only Lambda can reach the database on 6379.
  The database instance has an outbound public IP for image downloads and SSM;
  it has no public inbound rule, SSH port, or public database access.
- A Lambda execution role with network/log permissions and no model permissions.
  The older `infra/template.yaml` stack is untouched.

The Lambda URL is publicly reachable but tool calls require a token. There is no
custom domain, ALB, NAT gateway, GitHub OAuth, reviewer, or paid-model integration.
The always-on instance, its public IPv4, disks, snapshots, and Lambda/log usage are
billable. An administrator should confirm regional pricing and a budget before deployment.
This is a small-team pilot, not a highly available production backend.

AWS documents [Function URL HTTPS](https://docs.aws.amazon.com/lambda/latest/dg/urls-invocation.html),
[its invocation permissions](https://docs.aws.amazon.com/lambda/latest/dg/urls-auth.html),
and the [Lambda Web Adapter](https://github.com/aws/aws-lambda-web-adapter).
The template includes both required URL invocation permissions. API authentication
is enforced in MidFlight; teammates do not need AWS credentials.

### Prepare the deployment

Run from the collaboration repository on `codex/shared-backend`:

```sh
uv sync --locked --extra falkordb --extra demo
uv run --extra falkordb --extra demo python -m midflight.communication.provision \
  --project teammate-pilot --roster infra/shared/roster.example.json \
  --output "$HOME/.midflight-shared/teammate-pilot"
uv run --extra falkordb --extra demo python infra/shared/package.py
uv run --extra falkordb --extra demo python infra/shared/deploy.py \
  --profile midflight-dev --config "$HOME/.midflight-shared/teammate-pilot/config.json"
```

The provisioner refuses to overwrite an existing directory. Customize the roster
before provisioning for a different project; the example models the delivery demo.
Token files are private (0600); config contains SHA256 token hashes, never raw tokens.
Keep all of these files outside Git. Give each teammate only their own `.token` file
through a private channel. Never give them another agent's credential.

The deployment script verifies the expected AWS account and previews changes to only
`midflight-shared-communication`. It creates a dedicated private, versioned S3 artifact
bucket if absent and uploads the package; the preview does not apply stack resources.
Read the resource list, especially volume/instance replacements. Apply its exact ID:

```sh
uv run --extra falkordb --extra demo python infra/shared/deploy.py \
  --profile midflight-dev --execute CHANGE_SET_ID
aws cloudformation describe-stack-events --profile midflight-dev --region us-east-1 \
  --stack-name midflight-shared-communication
aws cloudformation describe-stacks --profile midflight-dev --region us-east-1 \
  --stack-name midflight-shared-communication --query 'Stacks[0].Outputs'
```

Database bootstrap takes time after EC2 creation. Wait for stack completion and a
successful `/healthz`; CloudFormation completion alone does not prove the database
container is running. Do not distribute a URL until an authenticated two-client
exchange succeeds. No AWS deployment has yet been validated by this branch.

The deployment role needs CloudFormation change-set/stack management, the template's
EC2/VPC/EBS resources, Lambda and Function URL management, IAM role creation and
PassRole for these stack roles, log groups, artifact-bucket S3 access, and SSM AMI
parameter reads. Database maintenance uses SSM. Have an account administrator provide
a scoped deployment role; do not attach broad administrator permissions to teammates.
Current permission failures: `ec2:DescribeVpcs`, `cloudformation:ListStacks`, and
`iam:ListAttachedUserPolicies`. Merely adding these read permissions is not enough
to create the resources in the template.

### Connect a teammate

Clone this branch and run the locked dependency install above. No local Docker or
FalkorDB is needed for a remote coding session. Configure a stdio MCP server named
`midflight` in the coding client with these values (substitute absolute paths):

```json
{
  "command": "/absolute/path/midflight-agent-collaboration/.venv/bin/python",
  "args": ["-m", "midflight.communication.mcp"],
  "env": {
    "MIDFLIGHT_URL": "https://YOUR-ID.lambda-url.us-east-1.on.aws",
    "MIDFLIGHT_TOKEN_FILE": "/absolute/private/path/billing.token"
  }
}
```

For the existing Codex CLI, the corresponding project/client MCP configuration is:

```toml
[mcp_servers.midflight]
command = "/absolute/path/midflight-agent-collaboration/.venv/bin/python"
args = ["-m", "midflight.communication.mcp"]

[mcp_servers.midflight.env]
MIDFLIGHT_URL = "https://YOUR-ID.lambda-url.us-east-1.on.aws"
MIDFLIGHT_TOKEN_FILE = "/absolute/private/path/billing.token"
```

Merge this entry into the client's configuration; do not replace unrelated settings.
Use the agent name assigned to that token when joining. For example: “Implement
billing. Join MidFlight as billing and follow relevant published interfaces.”
Use your real component task and repository. Each machine can create/resume its own
sessions. Consumers need not acknowledge compatible publications. Resolve genuine
incompatibilities through discussion and explicit author-resolved objections.

The four-panel harness remains a local demonstration. Its Reset must not wipe a
shared team project, and it has not been converted into a remote-team launcher.

## Operations and limitations

- Restarting the API preserves state. Bootstrap fills only missing roster/ownership
  entries; it must not undo agent subscriptions or ownership transfers.
- Restarting FalkorDB relies on the retained AOF volume. Before upgrades, quiesce
  writers, stop the database cleanly, and snapshot the data volume. Test restoring
  a snapshot to a separate instance before relying on it as a backup. Scheduled
  backups and disaster-recovery exercises are not implemented yet.
- Do not delete the stack casually: the volume uses a deletion snapshot, not a live
  replacement database. Updates retain replaced data volumes. Replacement can incur
  downtime; never approve an unexplained volume replacement. Artifact versions and
  snapshots can continue costing money after stack deletion.
- Credential revocation/rotation is an operator action: remove the old hash, add a
  new random token's SHA256 hash for the same identity, and redeploy. The Lambda
  configuration update replaces environments. Wait for completion before treating
  revocation as effective. In-flight calls may complete. There is no self-service
  account management, expiry, or per-person audit beyond the assigned agent identity.
- Authenticated collaborators can edit their topic subscriptions and exchange direct
  messages. Routing is structural; it does not classify the semantics of prose.
- State is one JSON snapshot per project plus graph projection; growth/load limits
  have not been benchmarked. The API caps request bodies at 64 KiB. There is no
  dedicated per-credential rate limiting, WAF, or availability SLA. Public invalid
  requests can still incur Lambda invocation cost.
- HTTP tests establish transport/persistence behavior, not that an LLM read or applied
  a requirement. Shared Git integration and actual combined-code tests remain explicit.

For a standalone VM with a domain, `infra/shared/compose.yml` is an alternative
container deployment using Caddy HTTPS. It is not required for the AWS Function URL.
Set `MIDFLIGHT_DOMAIN` and `MIDFLIGHT_CONFIG_PATH`; install the hash-only server config
readable by container UID 10001 (e.g. `install -o 10001 -g 10001 -m 400`). Only ports
80/443 are published. Persist and privately back up its Docker volumes. This alternative
has not been validated on a remote host.

## Validation performed on this branch

- Full suite with an isolated FalkorDB container: **602 passed**.
- Two independent stdio MCP subprocesses called a real HTTPS server using a locally
  trusted test certificate. After killing and restarting the server, an identical
  policy retry returned its original event ID and the other client retrieved it.
- API tests cover project/agent/session isolation, strict input types, concurrent
  publication conflicts, duplicate writes, exact objections and author-only resolution,
  selective policy routing, supersession, independent cursors, ownership transfer
  recovery, and oversized-request rejection.
- Lint, terminal-highlighting checks, Compose configuration validation, and
  CloudFormation `cfn-lint` passed. The Docker image and ARM64 Lambda archive build.
- These are local transport tests, not a test on two physical computers or a live
  AWS deployment. No new real-agent rehearsal or human requirement interpretation
  was performed for this transport change. Earlier rehearsal evidence stays unchanged.
