# Isolated worker admission contract

This small, dependency-free Python module is an offline contract prototype. It
does not connect to Hermes Cloud, Honey Core, GitHub, a model, or a Control
Center. It has no publisher and cannot commit, push, merge, deploy, or change
policy.

The adapter accepts five receipts from an external trust boundary: assigned
task, worker identity, signed lease, authenticated live Guard snapshot, and
Hermes artifact provenance. It hashes the original byte payload, binds the
task to a Hermes session, checks the pinned Hermes version/commit and target
path, and rejects path aliases, case-fold collisions, non-NFC paths and
file/directory overlap. The implementation intentionally does not verify
signatures or mint receipts. The verifier must check canonical lease revocation
at each publish gate and must authenticate source provenance.

The SQLite ledger is only a local replay/crash-recovery aid. It is not a
canonical nonce store, writer census, lease issuer, or remote CAS. Immediately
before a write, `begin_publication` revalidates identity, current lease and
revocation, the lease scope/TTL, live Guard freshness, source SHA, fence epoch,
and exclusive-writer count. Its states are `reserved` (no publisher attempt
entered), `effect_unknown` (a publisher attempt may have reached GitHub), and
`completed` (a matching external publication receipt was authenticated by a
supplied verifier and recorded). An `effect_unknown` task cannot be republished
until an independent canonical receipt reconciles it. The offline prototype
has no real verifier or publisher and performs no write; local checks are not
an atomic Guard/GitHub CAS. Old unscoped reservations migrate to
`legacy_unscoped` and fail closed rather than being treated as fresh tasks.

A duplicate task is a no-op; a reused task ID with changed evidence or a nonce
collision is rejected. A publication receipt must bind the task, original
Hermes session, artifact SHA/size, pinned producer, GitHub broker identity,
repository/branch/base/commit, lease ID/nonce and fence generation/epoch.
`hermes chat --query-file ... --oneshot` and
`hermes sessions export --session-id ... --redact` are documented Hermes CLI
interfaces, but a redacted session export is transcript evidence, not the
original file bytes or a provider-signed artifact receipt. This LAB contains
only the fail-closed interface and synthetic tests; it does not prove that
Hermes Cloud exposes a supported original-byte handoff. These transitions are
not a claim of exactly-once delivery; real completion depends on an
independently authenticated GitHub receipt and canonical Guard state.

Run only this new focused test file:

```sh
python3 -m unittest discover -s hermes_worker_lab -t . -v
```
