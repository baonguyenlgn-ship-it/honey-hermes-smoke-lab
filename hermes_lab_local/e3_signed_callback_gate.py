"""E3 TEST-only worker callback verification; never mints worker authority.

Requires separately verified Owner intent and independently pinned enrolled
host public key, plus exact GitHub run/ledger evidence. Does not send a
callback, write Git, claim a lease or establish a Codespace custodian. A PASS
means *eligibility for independently authorized delivery*, never delivery.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import json
import re
from typing import Mapping

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from .e3_owner_comment_admission import (
    AUDIENCE as OWNER_AUD, EXPECTED_HEAD, PR_NUMBER, REPO,
)

AUDIENCE = "honey.hermes.e3.signed-host-worker-callback.v1"
TASK = "HERMES-E3-OWNER-AUTHORIZED-TEST-ONLY"
HEX64 = re.compile(r"^[0-9a-f]{64}$")
JTI = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9:_-]{16,127}$")
FIELDS = frozenset({
    "aud", "repo", "pr", "pr_head", "owner_comment_id", "task_id",
    "lease_jti", "runtime_permit_sha256", "host_id", "issuer_id",
    "worker_actor", "worker_run_id", "worker_source_sha256",
    "worker_qa_status", "callback_id", "issued_at", "expires_at",
    "production_authorized", "paid_provider_allowed",
})

class CallbackDenied(ValueError):
    pass

def canonical(value: Mapping) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",",":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")

def verify_signed_callback_eligibility(
    signed: Mapping,
    *,
    enrolled_public_key: bytes,
    independently_verified_owner_intent: Mapping,
    verified_worker_run: Mapping,
    verified_ledger: Mapping,
    expected_host_id: str,
    expected_issuer_id: str,
    expected_worker_actor: str,
    now: int,
) -> dict:
    """Return an eligibility proof only; caller must do durable CAS separately.

    enrolled_public_key MUST come from already verified protected host custody,
    never a GitHub PR comment, CI secret or request-supplied public key.
    verified_worker_run and verified_ledger MUST be separately fetched from
    their protected authoritative stores. A unit test fixture proves neither.
    """
    if type(now) is not int or not isinstance(enrolled_public_key,bytes) or len(enrolled_public_key)!=32:
        raise CallbackDenied("E3_TRUST_ANCHOR_INVALID")
    if not isinstance(signed,dict) or set(signed)!={"claims","sig_b64"}:
        raise CallbackDenied("E3_CALLBACK_SHAPE_INVALID")
    c=signed["claims"]
    if not isinstance(c,dict) or set(c)!=FIELDS or not isinstance(signed["sig_b64"],str):
        raise CallbackDenied("E3_CALLBACK_CLAIMS_INVALID")
    try:
        signature=base64.b64decode(signed["sig_b64"],validate=True)
        if len(signature)!=64: raise ValueError("bad signature size")
        Ed25519PublicKey.from_public_bytes(enrolled_public_key).verify(
            signature,canonical(c))
    except (ValueError,TypeError,InvalidSignature,binascii.Error):
        raise CallbackDenied("E3_CALLBACK_SIGNATURE_NOT_VERIFIED") from None
    owner=independently_verified_owner_intent
    if (not isinstance(owner,dict)
            or owner.get("aud")!=OWNER_AUD
            or owner.get("status")!="AUTHENTICATED_OWNER_READONLY_INTENT_NOT_EXECUTED"
            or owner.get("repo")!=REPO
            or owner.get("pr")!=PR_NUMBER
            or owner.get("pr_head")!=EXPECTED_HEAD
            or owner.get("execution_authorized") is not False
            or owner.get("runtime_permit_issued") is not False):
        raise CallbackDenied("E3_OWNER_INTENT_NOT_PROVEN")
    if (c["aud"]!=AUDIENCE
            or c["repo"]!=REPO
            or type(c["pr"]) is not int or c["pr"]!=PR_NUMBER
            or c["pr_head"]!=EXPECTED_HEAD
            or type(c["owner_comment_id"]) is not int
            or c["owner_comment_id"]!=owner.get("comment_id")
            or c["task_id"]!=TASK
            or not isinstance(c["lease_jti"],str) or not JTI.fullmatch(c["lease_jti"])
            or not isinstance(c["runtime_permit_sha256"],str)
            or not HEX64.fullmatch(c["runtime_permit_sha256"])
            or c["host_id"]!=expected_host_id
            or c["issuer_id"]!=expected_issuer_id
            or c["worker_actor"]!=expected_worker_actor
            or type(c["worker_run_id"]) is not int or c["worker_run_id"]<=0
            or not isinstance(c["worker_source_sha256"],str)
            or not HEX64.fullmatch(c["worker_source_sha256"])
            or c["worker_qa_status"]!="INDEPENDENT_QA_PASS"
            or not isinstance(c["callback_id"],str)
            or c["callback_id"]!="cb-"+hashlib.sha256(
                (REPO+"|"+c["lease_jti"]+"|"+str(c["worker_run_id"])).encode()
            ).hexdigest()
            or c["production_authorized"] is not False
            or c["paid_provider_allowed"] is not False):
        raise CallbackDenied("E3_CALLBACK_BOUND_SCOPE_MISMATCH")
    if (type(c["issued_at"]) is not int or type(c["expires_at"]) is not int
            or not c["issued_at"]<=now<c["expires_at"]
            or c["expires_at"]-c["issued_at"]>300):
        raise CallbackDenied("E3_CALLBACK_NOT_FRESH")
    run=verified_worker_run
    if (not isinstance(run,dict)
            or run.get("id")!=c["worker_run_id"]
            or run.get("repository",{}).get("full_name")!=REPO
            or run.get("head_sha")!=EXPECTED_HEAD
            or run.get("status")!="completed"
            or run.get("conclusion")!="success"):
        raise CallbackDenied("E3_INDEPENDENT_WORKER_RUN_NOT_PROVEN")
    ledger=verified_ledger
    if (not isinstance(ledger,dict)
            or ledger.get("jti")!=c["lease_jti"]
            or ledger.get("owner_comment_id")!=c["owner_comment_id"]
            or ledger.get("runtime_permit_sha256")!=c["runtime_permit_sha256"]
            or ledger.get("worker_run_id")!=c["worker_run_id"]
            or ledger.get("worker_source_sha256")!=c["worker_source_sha256"]
            or ledger.get("status")!="CLAIMED_COMPLETED_QA_PASS"
            or ledger.get("callback_consumed") is not False):
        raise CallbackDenied("E3_INDEPENDENT_PROTECTED_LEDGER_NOT_PROVEN")
    return {
        "status":"E3_SIGNED_CALLBACK_ELIGIBLE_NOT_DELIVERED",
        "callback_id":c["callback_id"],
        "worker_run_id":c["worker_run_id"],
        "worker_source_sha256":c["worker_source_sha256"],
        "owner_comment_id":c["owner_comment_id"],
        "ledger_write_performed":False,
        "callback_delivered":False,
        "signer_issued_here":False,
        "model_executed_here":False,
        "auto_next_dispatched":False,
        "production_authorized":False,
    }
