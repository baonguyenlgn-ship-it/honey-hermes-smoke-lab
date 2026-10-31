"""Supervised, *host-only* bridge from signed one-use admission to the existing Hermes LAB loop.

This does not issue leases, re-use old consent, call a paid fallback, or certify Gate B.
Only the enrolled Codespace custodian may invoke it with a fresh current signed JTI.
Any uncertain model/broker outcome consumes the admission: never retry blindly.
"""
from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
import time
from pathlib import Path

from .v31.execution_adapter import claim, prepare
from .v31.gate_bridge import fetch_snapshot, fetch_live_consent
from .v31.host_authority import ROOT as AUTH_ROOT, fence_check, trusted_context
from .v31.one_use_lease_gate import AdmissionDenied, MODEL, HOST

REPO_ROOT = Path(__file__).resolve().parents[1]
FREE_EVIDENCE = AUTH_ROOT / "nous-account-free-readback.json"
LEASE_FILE = AUTH_ROOT / "current-lease.json"
MAX_EVIDENCE_AGE_SECONDS = 120
REPAIR_SCRIPT = ("bash", "hermes_lab_local/codespaces_repair_loop.sh")
BROKER_COMMAND = (sys.executable, "-m", "hermes_lab_local.repair_broker")


def verify_free_account_evidence(evidence, *, now: int) -> None:
    """Validate a fresh account-specific statement, not a public model catalog.

    Evidence must be created by the authenticated *host operator* after a
    real Nous account/read-only billing readback. These bytes are not a
    provider-signed attestation; external custody/accuracy must be checked.
    """
    if not isinstance(evidence, dict) or set(evidence) != {
        "schema", "source", "plan", "model_id", "account_free_verified",
        "input_usd_per_million", "output_usd_per_million", "observed_at",
        "no_paid_fallback",
    }:
        raise AdmissionDenied("FREE_ACCOUNT_EVIDENCE_MISSING")
    if (
        evidence["schema"] != "honey.hermes.host-free-account-readback.v1"
        or evidence["source"] != "AUTHENTICATED_NOUS_ACCOUNT"
        or evidence["plan"] != "FREE"
        or evidence["model_id"] != MODEL
        or evidence["account_free_verified"] is not True
        or evidence["no_paid_fallback"] is not True
        or type(evidence["input_usd_per_million"]) not in (int, float)
        or type(evidence["output_usd_per_million"]) not in (int, float)
        or evidence["input_usd_per_million"] != 0
        or evidence["output_usd_per_million"] != 0
        or type(evidence["observed_at"]) is not int
        or not 0 <= now - evidence["observed_at"] <= MAX_EVIDENCE_AGE_SECONDS
    ):
        raise AdmissionDenied("NO_VERIFIED_ZERO_COST_FREE_ACCOUNT")


def protected_json(path: Path):
    """Read nonsecret evidence from the already protected host directory."""
    try:
        root_st = os.lstat(AUTH_ROOT)
        st = os.lstat(path)
        if (
            not stat.S_ISDIR(root_st.st_mode)
            or root_st.st_uid != 1000
            or stat.S_IMODE(root_st.st_mode) & 0o077
            or not stat.S_ISREG(st.st_mode)
            or st.st_uid != 1000
            or stat.S_IMODE(st.st_mode) & 0o177
            or st.st_nlink != 1
            or st.st_size > 4096
        ):
            raise AdmissionDenied("HOST_EVIDENCE_NOT_PROTECTED")
        with path.open("rb") as handle:
            obj = json.loads(handle.read(4097))
        if not isinstance(obj, dict):
            raise AdmissionDenied("HOST_EVIDENCE_NOT_OBJECT")
        return obj
    except (OSError, ValueError, UnicodeDecodeError):
        raise AdmissionDenied("HOST_EVIDENCE_UNAVAILABLE") from None


def run_supervised_once(live_comment_id: int, *, run_command=None):
    """Run only after FRESH dual consent, zero-charge host readback and durable claim.

    This entrypoint is explicitly invoked by the host custodian; no watcher.
    Caller-supplied GitHub comments, public tokens, or model output cannot
    establish issuer identity, free pricing or protected ledger.
    """
    if (
        os.geteuid() != 1000
        or os.environ.get("CODESPACES") != "true"
        or os.environ.get("CODESPACE_NAME") != HOST
        or type(live_comment_id) is not int
        or live_comment_id <= 0
    ):
        raise AdmissionDenied("AUTHORIZED_CODESPACE_OPERATOR_REQUIRED")
    bundle = protected_json(LEASE_FILE)
    host = trusted_context(bundle)
    fence_check(bundle)
    now = int(time.time())
    verify_free_account_evidence(protected_json(FREE_EVIDENCE), now=now)
    pr, legacy = fetch_snapshot()
    live = fetch_live_consent(live_comment_id)
    # No effect: this check must complete before consuming one-use admission.
    prepare(pr, legacy, bundle, host, live, now=now)
    pr_again, _ = fetch_snapshot()
    receipt = claim(pr, legacy, pr_again, bundle, host, live, now=int(time.time()))
    if receipt.get("status") != "CLAIMED_NOT_EXECUTED" or receipt.get("owner_live_comment_id") != live_comment_id:
        raise AdmissionDenied("AUTHENTICATED_ONCE_ONLY_CLAIM_MISSING")
    # Once claimed, an error / crash is NOT retried: ledger remains consumed.
    # The existing script drops GitHub tokens and invokes uid999 in a private LAB.
    runner = subprocess.run if run_command is None else run_command
    try:
        first = runner(REPAIR_SCRIPT, cwd=REPO_ROOT, check=False, timeout=240)
    except (OSError, subprocess.TimeoutExpired):
        raise AdmissionDenied("MODEL_OUTCOME_UNKNOWN_NO_RETRY") from None
    if first.returncode != 0:
        raise AdmissionDenied("MODEL_OR_QA_BLOCKED_NO_RETRY")
    try:
        pushed = runner(BROKER_COMMAND, cwd=REPO_ROOT, check=False, timeout=90)
    except (OSError, subprocess.TimeoutExpired):
        raise AdmissionDenied("BROKER_OUTCOME_UNKNOWN_RECONCILE_NO_RETRY") from None
    if pushed.returncode != 0:
        raise AdmissionDenied("BROKER_FAILED_RECONCILE_REMOTE_NO_RETRY")
    return {
        "status": "HOST_EXECUTED_AWAITING_INDEPENDENT_WINDOWS_QA",
        "jti": bundle["claims"]["jti"],
        "live_comment_id": live_comment_id,
        "gate_b": "NOT_PROVEN",
    }


def main():
    # Do not use this entrypoint without an actual fresh Owner JTI-bound comment.
    if len(sys.argv) != 2 or not sys.argv[1].isdigit():
        raise SystemExit("USAGE: python -m hermes_lab_local.live_execution_gate LIVE_COMMENT_ID")
    try:
        receipt = run_supervised_once(int(sys.argv[1]))
    except AdmissionDenied as exc:
        raise SystemExit("HERMES_GATE_B_BLOCKED_" + str(exc)) from None
    print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()
