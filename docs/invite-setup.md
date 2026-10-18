# Try an isolated cloud demo through an invite

Open the invite link, select **Create my demo**, and save `midflight-access.json`.
The page shows the install command. Each redemption creates a new four-agent project;
visitors do not join Frederik's team or another visitor's workspace.

Prerequisites: macOS, Git, uv, tmux, and Codex CLI signed in with
`~/.codex/auth.json`. Coding agents use the visitor's own account and allowance.
No AWS credentials, Docker or local database are needed. Other operating systems
and keychain-only/custom-CODEX_HOME login have not been verified for this harness.

```sh
git clone --branch codex/invite-onboarding https://github.com/MidFlightt/midflight-agent-collaboration.git midflight-demo
cd midflight-demo
uv sync --locked --extra falkordb --extra demo
uv run python -m midflight.communication.onboard --bundle "$HOME/Downloads/midflight-access.json"
```

Use a fresh clone directory and adjust the download path if necessary. The installer
writes separate private agent token files, starts isolated coding profiles and prints
a local browser address (port 18942 by default; override with `--port`). All four
prompts are unsent. Global MCP settings, previous runs and shared projects are unchanged.
The downloaded JSON is a credential: keep it private and outside Git. Installed token
files are mode 0600 in a mode 0700 directory. Never share an entire `runs/` directory.

Press Enter in each panel to begin. Follow [the recording workflow](recording-workflow.md)
for the fee change, one useful Billing follow-up, and operator combined-code validation.
A fresh invite redemption starts another isolated project. Cloud Reset cannot wipe
shared state; existing runs and their evidence are retained. Relaunching the same
access file reconnects to the same project, not a fresh scenario.

## Operator management

The deployment requires a stable private signing key and a separate operator token's
SHA256 hash. Supply them through `infra/shared/deploy.py --invite-secrets PRIVATE.json`
with `signing_key` and `admin_hash` fields. Subsequent deployments preserve these
CloudFormation NoEcho parameters when the flag is omitted. Keep the original signing
key with backups: changing it is rejected rather than silently breaking credential
recovery. The operator bearer token stays in a private file, not the deployment config.

Create an invite with the operator CLI (substitute the deployed HTTPS URL):

```sh
.venv/bin/python infra/shared/invite.py --url https://YOUR-ENDPOINT \
  --admin-token-file /private/operator.token --output /private/invite.json \
  --max-uses 20 --lifetime-hours 168 --access-hours 168
```

Share only the `url` in that output. Its secret is in the URL fragment, so ordinary
HTTP request URLs do not contain it. The page has no third-party scripts or analytics,
sets no-store and no-referrer, and exchanges the secret in a POST body. Browser history
and anyone receiving the full link can still hold access: this is an invitation, not
an identity check. Each invite allows at most 50 redemptions, seven days to redeem and
30 days of issued access; the defaults are 20 redemptions and seven days for both.

```sh
.venv/bin/python infra/shared/invite.py --url https://YOUR-ENDPOINT \
  --admin-token-file /private/operator.token --revoke INVITE_ID
```

Revocation rejects future redemptions and credentials issued by that invite, on their
next request. In-flight requests can finish. Data is retained; expiry is not deletion.
Invite expiry stops new redemptions; issued credentials have their own access expiry.
There is no automatic cleanup or self-service account recovery yet. Closing a browser
can lose its retry key; recovering a lost access file may require a new redemption.

## Persistence and boundaries

Invite metadata, hashed bearer credentials, project rosters and hashed redemption keys
are saved in a dedicated FalkorDB coordination registry using atomic CAS. Concurrent
last-place claims cannot exceed the limit. Repeating a redemption with the same random
request ID returns the same project and credentials without consuming another place.
Tokens are derived using the server's stable private key; plaintext tokens and link
secrets are not persisted in the registry. Client credentials bind one project and agent.
Existing statically provisioned projects continue to work unchanged.

This is bounded pilot onboarding, not open public registration: there is no per-IP
rate limiting, automated billing protection or automated database disaster recovery.
Anyone with a link can consume its remaining places. Revoke leaked links. Do not
publish operator tokens, raw access bundles, or the signing key in the repository.
