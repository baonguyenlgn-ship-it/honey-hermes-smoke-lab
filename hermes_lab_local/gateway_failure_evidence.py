"""Hermes gateway error triage without credential disclosure or model retry.

Only interprets evidence *already captured* on an approved host; never
reads files outside explicit CLI argument, starts an agent, or claims a
signed provider identity. No raw log line is ever returned to the caller.

This is a diagnostic tool, NOT Gate-B authorization or provider QA.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

MAX_LOG_BYTES = 65536

# Strict, deliberately incomplete signatures from Hermes upstream issue
# reports. A recognized signature is not enough to prove causal ownership.
SIGNATURES = (
    ("CUSTOM_PROVIDER_UNBOUND", re.compile(
        r"provider ['\"]custom['\"] resolved without credentials", re.I)),
    ("GATEWAY_SESSION_BUSY", re.compile(
        r"RuntimeStoreError: session_busy", re.I)),
    ("CUSTOM_ENDPOINT_HTTP_401", re.compile(
        r"(?:HTTP|Error code:)\s*401\b", re.I)),
    ("LOCAL_ENDPOINT_UNREACHABLE", re.compile(
        r"(?:Connection refused|ConnectError|ECONNREFUSED)", re.I)),
    ("CONTEXT_COMPRESSION_FAILURE", re.compile(
        r"(?:compression exhaustion|context.overflo\w*)", re.I)),
    ("MODEL_RATE_LIMIT", re.compile(
        r"(?:HTTP|Error code:)\s*429\b", re.I)),
    ("PROVIDER_REQUEST_REJECTED", re.compile(
        r"(?:HTTP|Error code:)\s*400\b", re.I)),
    ("GATEWAY_GENERIC_FAILURE_ONLY", re.compile(
        r"Something went wrong and I couldn't finish this reply", re.I)),
)

def diagnose(log_text: str) -> dict:
    """Closed-set redaction-safe classification. Outputs no user log bytes."""
    result = {
        "schema": "honey.hermes.gateway-failure-evidence.v1",
        "source_is_provider_signed": False,
        "auto_retry_authorized": False,
        "live_model_call_performed": False,
        "production_authorized": False,
        "details_disclosed": False,
        "root_cause_proven": False,
    }
    if not isinstance(log_text, str) or len(log_text.encode("utf-8")) > MAX_LOG_BYTES:
        return dict(result, classification="INVALID_OR_OVERSIZE_LOG",
                    next_safe_step="STOP_UNTRUSTED_GATEWAY_EVIDENCE")
    for code, pattern in SIGNATURES:
        if pattern.search(log_text):
            return dict(result, classification=code,
                next_safe_step=("COLLECT_PRIVATE_GATEWAY_LOG_ON_ENROLLED_HOST"
                                if code == "GATEWAY_GENERIC_FAILURE_ONLY"
                                else "VERIFY_ORIGINAL_HOST_LOG_AND_ROUTE_BEFORE_RETRY"))
    return dict(result, classification="UNCLASSIFIED_NO_ROOT_CAUSE_PROOF",
                next_safe_step="COLLECT_PRIVATE_GATEWAY_LOG_ON_ENROLLED_HOST")

def diagnose_bounded_file(path: Path) -> dict:
    """Read only a caller-chosen local file; reject symlink, size, invalid UTF8."""
    import os
    import stat
    try:
        st = os.lstat(path)
        if (not stat.S_ISREG(st.st_mode) or st.st_nlink != 1
                or st.st_size > MAX_LOG_BYTES
                or st.st_size < 0):
            return diagnose(None)
        with open(path, "rb") as f:
            raw = f.read(MAX_LOG_BYTES + 1)
        if len(raw) > MAX_LOG_BYTES:
            return diagnose(None)
        return diagnose(raw.decode("utf-8", "strict"))
    except (OSError, UnicodeError):
        return diagnose(None)

def main():
    if len(sys.argv) != 2:
        raise SystemExit("USAGE: python -m hermes_lab_local.gateway_failure_evidence /path/to/approved/gateway.log")
    print(json.dumps(diagnose_bounded_file(Path(sys.argv[1])),sort_keys=True))
    # Inability to prove a root cause is a block, never a PASS exit.
    raise SystemExit(2)

if __name__ == "__main__":
    main()
