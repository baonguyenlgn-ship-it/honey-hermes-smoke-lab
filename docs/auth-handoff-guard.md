# Hermes LAB authorization handoff guard

This is a credential-free, non-dispatched handoff validator. It does not call
Hermes, Nous, GitHub, Actions, or any remote service, and it never publishes a
branch or pull request. Its fixtures are synthetic.

## What it fences

- Exact task ID, Hermes source session matched against the independently assigned
  session ID, pinned source commit, LAB base commit,
  safe filename, byte count, SHA-256, and task-specific branch name.
- A duplicate task with the same artifact and commit is a no-op. A reused task
  ID with changed data, an occupied task branch, or a mismatch between the task
  ledger and branch ref fails closed.
- Non-secret authorization claims must identify only
  `baonguyenlgn-ship-it/honey-hermes-smoke-lab`, expire in the future, and grant
  only `contents:write`, `pull_requests:write`, and optional `metadata:read`.
  The issue/expiry timestamps are limited to a 10-minute grant lifetime.
- Known secret values, GitHub token forms, and PEM private-key blocks are
  redacted from diagnostic text.

## Security boundary

`expected_source_session` must come from the authenticated task assignment, not
from the artifact manifest. `AuthorizationClaims` contains claims only; its
issue/expiry timestamps and permissions must come from a trusted, provider-
verified credential broker. The harness cannot prove that provenance. Never
pass a bearer token, PAT, OAuth
refresh token, or app private key into this module. This local harness does not
prove the actual permissions of any token and cannot publish. A publisher must
re-read the target repository and base SHA immediately before writing, use a
short-lived repository-scoped token, create only a new task branch and Draft
PR, verify the GitHub readback SHA, and record a task-idempotency receipt.

Hermes Cloud dashboard v0.22.5 exposes MCP transports with `None`, `Bearer`, or
`OAuth` auth. The UI's Keys page says values are stored in `~/.hermes/.env` and
written to disk immediately; masked UI output is not evidence of encrypted
provider custody. The OAuth selector says it opens authentication in the
browser running on the dashboard backend. This module therefore does not store
or use a GitHub credential.

## Run tests

```sh
python -m unittest discover -s tests -v
```
