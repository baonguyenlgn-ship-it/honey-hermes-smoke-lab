"""Strict Gate B receipt classifier for an independently fetched GitHub Actions run.

Checks integrity and limited Windows QA evidence but NEVER certifies a real
provider-driven QA-fail→repair cycle from a broker's self-reported receipt.
NOT a publisher, writer, or execution method.
"""
from __future__ import annotations
import hashlib
import re
from typing import Mapping
from .one_use_lease_gate import AdmissionDenied, REPO, BRANCH, MODEL

RECEIPT_KEYS = frozenset({
    "schema", "task_id", "model", "sha256", "size", "attempts",
    "repairs", "hermes_sha", "provider_origin_signed",
    "core_guard_authorized", "production_authorized",
    "unattended_execution_authorized",
})
RUN_NAME = "Hermes LAB real repair artifact Windows readback"
HERMES_SHA = "bf0203a794a07aac3ff764972ab9087baa4e4f4e"
BROKER_TASK = "hermes-lab-rename-label-v1"


def classify_windows_readback(receipt: Mapping, source: bytes, run: Mapping,
                              *, original_head: str) -> dict:
    """Process only bytes + metadata independently retrieved by a trusted QA reader.

    A string/dict from a chat or a model is NOT trusted independent readback.
    Do not pass caller-generated values in place of GitHub official API data.
    """
    if not isinstance(source, bytes) or not 20 <= len(source) <= 2048:
        raise AdmissionDenied("SOURCE_BYTES_INVALID")
    if not isinstance(receipt, dict) or set(receipt) != RECEIPT_KEYS:
        raise AdmissionDenied("READBACK_RECEIPT_FIELDS_INVALID")
    if (receipt["schema"] != "honey.hermes.lab-repair-readback.v1"
            or receipt["task_id"] != BROKER_TASK
            or receipt["model"] != MODEL
            or receipt["hermes_sha"] != HERMES_SHA
            or any(receipt[k] is not False for k in (
                "provider_origin_signed", "core_guard_authorized",
                "production_authorized", "unattended_execution_authorized"))):
        raise AdmissionDenied("RECEIPT_SCOPE_OR_AUTHORITY_INVALID")
    if (type(receipt["attempts"]) is not int or not 1 <= receipt["attempts"] <= 3
            or type(receipt["repairs"]) is not int
            or receipt["repairs"] != receipt["attempts"] - 1):
        raise AdmissionDenied("REPAIR_ATTEMPTS_INVALID")
    digest = hashlib.sha256(source).hexdigest()
    if (type(receipt["size"]) is not int or receipt["size"] != len(source)
            or receipt["sha256"] != digest):
        raise AdmissionDenied("READBACK_SOURCE_SHA_MISMATCH")
    try: source.decode("utf-8", errors="strict")
    except UnicodeDecodeError: raise AdmissionDenied("READBACK_INVALID_UTF8") from None
    if (not isinstance(run, dict) or type(run.get("id")) is not int
            or run["id"] <= 0 or run.get("name") != RUN_NAME
            or run.get("status") != "completed" or run.get("conclusion") != "success"
            or run.get("event") != "push" or run.get("head_branch") != BRANCH
            or (run.get("repository") or {}).get("full_name") != REPO
            or not isinstance(run.get("head_sha"), str)
            or not re.fullmatch(r"[0-9a-f]{40}", run["head_sha"])
            or run["head_sha"] == original_head):
        raise AdmissionDenied("WINDOWS_QA_RUN_NOT_VERIFIED")
    # Broker receipt does not include trustworthy provider turn ids or
    # independently signed QA rejection-feedback provenance. A repairs count
    # of 1 or 2 is NOT proof that the model actually repaired anything.
    return {
        "artifact_integrity": "SHA_MATCH_ONLY",
        "windows_workflow": "REPORTED_SUCCESS_NEEDS_INDEPENDENT_LOG_READBACK",
        "run_id": run["id"],
        "commit_sha": run["head_sha"],
        "artifact_sha256": digest,
        "reported_repair_turns": receipt["repairs"],
        "gate_b": "NOT_PROVEN",
        "missing": "real provider turn evidence, independent QA fail→feedback→fix, Windows job/log readback",
    }
