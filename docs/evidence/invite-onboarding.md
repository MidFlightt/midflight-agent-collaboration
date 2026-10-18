# Invite onboarding validation — 2026-10-18 UTC

Deployed bounded, isolated-demo invite redemption to the existing AWS backend. The
CloudFormation update changed the Lambda package/configuration; it added no servers
or storage and preserved existing project credentials and data.

Measured checks:

- 612 repository tests passed with an isolated real FalkorDB fixture. Invite coverage
  includes expiry, revocation, stable retries, concurrent final-place redemption,
  project/agent isolation, registry recovery and safe local credential installation.
- The browser JavaScript check exercised a failed redemption followed by a retry using
  the same request ID, download content, re-download and displayed setup commands.
- The live HTTPS invite landing page displayed the correct available places and expiry.
- Two live redemptions produced different project IDs. Repeating a redemption returned
  identical access; a third fresh request exceeded the two-place test limit (409).
- All four issued agent credentials joined their isolated cloud project. Cross-agent
  and cross-project session access returned 403. Responses used Cache-Control: no-store.
- A fresh Git clone of the published branch installed successfully. Its onboarding CLI
  accepted the access file and launched four real Codex terminals with each task prompt
  present and unsent. No coding turns were submitted in this installer check.
- The disposable test run was archived and its controller closed. The test invite was
  revoked: its issued credential then returned 401 and redemption returned 403. Project
  data and local evidence were retained.
- Existing cloud protocol smoke checks passed again, including selective routing,
  supersession, objections, concurrent revisions and independent client recovery.

The new flow did not repeat the earlier real-agent coding rehearsal: that evidence is
in [cloud-agent-rehearsal.md](cloud-agent-rehearsal.md). Live browser download behavior
was not manually clicked; the page logic was tested with browser stubs, and the live
redemption API/access file/installer were tested separately. No second physical computer
or non-macOS client was tested. Production disaster recovery and rate limiting remain
outside this pilot.

Private raw evidence is under `runs/invite-deployment/` and the retained fresh clone
under `runs/invite-install-check/`. Those directories contain secrets and must not be
published. The separate shareable invite starts with 20 available demo projects, seven
days to redeem and seven days of access per redemption; it is not committed to Git.
