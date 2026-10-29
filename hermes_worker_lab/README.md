# Isolated worker admission contract

This small, dependency-free Python module is an offline contract prototype. It
does not connect to Hermes Cloud, Honey Core, GitHub, a model, or a Control
Center. It has no publisher and cannot commit, push, merge, deploy, or change
policy.

The adapter accepts only four receipts from an external trust boundary:
assigned task, worker identity, signed lease, and authenticated live Guard
snapshot. The implementation intentionally does not verify signatures or mint
receipts. Without an independently reviewed provider/Guard verifier it denies
all work. The tests use a fake verifier and synthetic claims; a passing test
does not enroll a worker or prove a real lease.

The SQLite ledger is only a local replay/crash-recovery aid. It is not a
canonical nonce store, writer census, lease issuer, or remote CAS. A duplicate
task is a no-op; a reused task ID with changed evidence or a nonce collision is
rejected. The prototype returns a scope decision and never executes the task.

Run only this new focused test file:

```sh
python3 -m unittest discover -s hermes_worker_lab -t . -v
```
