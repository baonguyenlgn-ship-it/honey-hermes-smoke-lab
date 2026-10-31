"""Deterministic bounded Honey Hermes LAB NEXT_SAFE_STEP planner.

A planner, NOT an executor, credential, signed attestation or GitHub reader.
Inputs must be independently reconciled by a trusted read-only verifier first.
Neither arbitrary backlog comments nor model-produced status can authorize work.
"""
from __future__ import annotations

import json
import re
from typing import Mapping

TASK = "LAB-NORMALIZE-REPAIR-V1"
MODEL = "upstage/solar-mini4:free"
BRANCH = "hermes-lab/actions-publisher-20261029-01"
MAX_REPAIRS = 2
SHA = re.compile(r"[a-f0-9]{40}\Z")

FIELDS = frozenset({
    "task_id", "model", "branch", "head", "verified_head", "lease_current",
    "live_consent_bound", "ledger_claimed", "attempt_started",
    "provider_ack_verified", "provider_error", "uncertain_effect",
    "qa_status", "qa_ref", "repairs", "published", "windows_verified",
    "callback_verified", "independent_evidence",
})


def _step(code: str, *, proceed: bool = False) -> dict:
    return {
        "schema": "honey.hermes.next-safe-step.v1",
        "task_id": TASK,
        "next_safe_step": code,
        "candidate_for_authorized_executor": proceed,
        "execution_authority_granted": False,
        "production_authorized": False,
    }


def next_safe_step(state: Mapping) -> dict:
    """Choose next narrowly allowed *candidate*, not grant execution.

    independent_evidence means the caller has verified provenance out-of-band;
    the bool itself is NOT an attestation. Never invoke with model-authored input.
    """
    if not isinstance(state, dict) or set(state) != FIELDS:
        return _step("STOP_UNTRUSTED_OR_INCOMPLETE_STATE")
    if (state["task_id"] != TASK or state["model"] != MODEL
            or state["branch"] != BRANCH or type(state["head"]) is not str
            or not SHA.fullmatch(state["head"])
            or state["verified_head"] != state["head"]):
        return _step("STOP_STALE_HEAD_OR_UNAPPROVED_TASK")
    bool_keys = FIELDS - {
        "task_id", "model", "branch", "head", "verified_head", "qa_status",
        "qa_ref", "repairs",
    }
    if any(type(state[x]) is not bool for x in bool_keys):
        return _step("STOP_UNTRUSTED_OR_INCOMPLETE_STATE")
    if (type(state["repairs"]) is not int
            or state["repairs"] < 0 or state["repairs"] > MAX_REPAIRS
            or state["qa_status"] not in ("NONE", "REJECT", "PASS")
            or type(state["qa_ref"]) is not str or len(state["qa_ref"]) > 250):
        return _step("STOP_INVALID_QA_HISTORY")
    if not state["independent_evidence"]:
        return _step("STOP_INDEPENDENT_READBACK_MISSING")
    if state["uncertain_effect"]:
        return _step("STOP_UNKNOWN_RECONCILE_NEVER_BLIND_RETRY")
    if state["provider_error"]:
        return _step("STOP_PROVIDER_FAILURE_NO_PAID_FALLBACK")
    if not state["lease_current"]:
        return _step("WAIT_HOST_CUSTODIAN_NEW_SCOPED_LEASE")
    if not state["live_consent_bound"]:
        return _step("WAIT_OWNER_CONSENT_FOR_EXACT_NEW_JTI")
    if not state["ledger_claimed"]:
        if state["attempt_started"] or state["provider_ack_verified"]:
            return _step("STOP_UNCLAIMED_EXECUTION_INCONSISTENCY")
        return _step("HOST_CUSTODIAN_CLAIM_ONCE")
    if not state["attempt_started"]:
        if state["provider_ack_verified"] or state["qa_status"] != "NONE":
            return _step("STOP_FABRICATED_MODEL_HISTORY")
        return _step("HOST_SUPERVISED_MODEL_FIRST_ATTEMPT")
    if not state["provider_ack_verified"]:
        return _step("STOP_MODEL_OUTCOME_UNKNOWN_NO_RETRY")
    if state["qa_status"] == "NONE":
        return _step("INDEPENDENT_QA_OF_REAL_CODE", proceed=True)
    if state["qa_status"] == "REJECT":
        if not state["qa_ref"]:
            return _step("STOP_QA_REJECTION_PROVENANCE_MISSING")
        if state["repairs"] >= MAX_REPAIRS:
            return _step("STOP_REPAIR_BUDGET_EXHAUSTED")
        return _step("HOST_BOUNDED_QA_TRIGGERED_REPAIR", proceed=True)
    if not state["qa_ref"]:
        return _step("STOP_INDEPENDENT_QA_PASS_EVIDENCE_MISSING")
    if not state["published"]:
        return _step("HOST_BROKER_PUBLISH_CAS", proceed=True)
    if not state["windows_verified"]:
        return _step("INDEPENDENT_WINDOWS_READBACK", proceed=True)
    if not state["callback_verified"]:
        return _step("VERIFY_DURABLE_OWNER_CALLBACK", proceed=True)
    return _step("WAIT_NEXT_EXPLICITLY_APPROVED_MISSION")


def main():
    import sys
    if len(sys.argv) != 2:
        raise SystemExit("USAGE: python -m hermes_lab_local.automatic_next_step <verified-state-json>")
    with open(sys.argv[1], encoding="utf-8") as handle:
        data = json.load(handle)
    print(json.dumps(next_safe_step(data), sort_keys=True))


if __name__ == "__main__":
    main()
