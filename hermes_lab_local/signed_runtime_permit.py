"""Verify a separately signed host TEST execution permit. Never issue one.

V3.1 admission always explicitly withholds execution and publication authority.
Only the enrolled operator's separately signed, fresh, exact-scope permission
could bridge that boundary. A permit cannot be supplied by a model, GitHub
comment, or ephemeral Windows job. Read of the protected permit file is the
caller's host-custody responsibility; no private signer key is used here.

This module performs NO execution, Git writes, issuing, or authority transfer.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import re
from typing import Mapping

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .v31.one_use_lease_gate import (
    AdmissionDenied, TrustedHostContext, REPO, BRANCH, TASK, MODEL, HOST,
    OUTPUT_PATHS, canonical_json, verify_signed_lease,
)

AUDIENCE = "honey.hermes.lab-host-runtime-permit.v1"
KEYS = frozenset({
    "aud", "issuer", "repo", "pr", "branch", "head", "task_id",
    "model", "host_id", "worker_actor", "broker_actor", "lease_jti",
    "lease_sha256", "owner_live_comment_id", "allowed_paths",
    "max_repairs", "issued_at", "expires_at", "mode", "cost_policy",
    "may_execute_model_once", "may_publish_test_artifact",
    "may_access_core", "may_merge_main", "may_deploy_production",
})


def verify_host_execution_permit(
    signed_permit: Mapping,
    signed_lease: Mapping,
    bound_ticket: Mapping,
    owner_live_comment_id: int,
    host: TrustedHostContext,
    *,
    now: int,
) -> dict:
    """Verify exact second permission after live Owner consent + lease checks.

    This is an eligibility check, not a right to start the worker. Caller
    must separately verify protected local custody, fence, zero-charge billing,
    durable once-only claim, role separation and the final broker CAS.
    """
    if not isinstance(host, TrustedHostContext):
        raise AdmissionDenied("HOST_CONTEXT_MISSING")
    if type(now) is not int or type(owner_live_comment_id) is not int or owner_live_comment_id <= 0:
        raise AdmissionDenied("INVALID_RUNTIME_PERMIT_TIME_OR_CONSENT")
    # Full Ed25519 verification of the ORIGINAL lease, not just matching
    # attacker-controlled unverified claim strings.
    claims = verify_signed_lease(signed_lease, bound_ticket, host, now=now)
    if (not isinstance(signed_permit, dict)
            or set(signed_permit) != {"claims", "sig_b64"}
            or not isinstance(signed_permit["claims"], dict)
            or set(signed_permit["claims"]) != KEYS):
        raise AdmissionDenied("RUNTIME_PERMIT_INVALID_SHAPE")
    p = signed_permit["claims"]
    sig = signed_permit["sig_b64"]
    if not isinstance(sig, str):
        raise AdmissionDenied("RUNTIME_PERMIT_SIGNATURE_MISSING")
    try:
        signature = base64.b64decode(sig, validate=True)
        if len(signature) != 64:
            raise ValueError("wrong signature size")
        Ed25519PublicKey.from_public_bytes(host.public_key_ed25519).verify(
            signature, canonical_json(p))
    except (ValueError, TypeError, InvalidSignature, binascii.Error):
        raise AdmissionDenied("RUNTIME_PERMIT_SIGNATURE_UNVERIFIED") from None

    digest = hashlib.sha256(canonical_json(signed_lease)).hexdigest()
    if (p["aud"] != AUDIENCE
            or p["issuer"] != host.custodian_id
            or p["repo"] != REPO
            or type(p["pr"]) is not int or p["pr"] != 4
            or p["branch"] != BRANCH
            or p["head"] != claims["head"]
            or p["task_id"] != TASK
            or p["model"] != MODEL
            or p["host_id"] != HOST or p["host_id"] != host.host_id
            or p["worker_actor"] != host.worker_actor
            or p["broker_actor"] != host.broker_actor
            or p["lease_jti"] != claims["jti"]
            or p["lease_sha256"] != digest
            or type(p["owner_live_comment_id"]) is not int
            or p["owner_live_comment_id"] != owner_live_comment_id
            or p["allowed_paths"] != list(OUTPUT_PATHS)
            or type(p["max_repairs"]) is not int or p["max_repairs"] != 2
            or p["mode"] != "isolated-lab-execute-once"
            or p["cost_policy"] != "no-new-billable-service"
            or p["may_execute_model_once"] is not True
            or p["may_publish_test_artifact"] is not True
            or p["may_access_core"] is not False
            or p["may_merge_main"] is not False
            or p["may_deploy_production"] is not False):
        raise AdmissionDenied("RUNTIME_PERMIT_SCOPE_MISMATCH")
    if (type(p["issued_at"]) is not int
            or type(p["expires_at"]) is not int
            or p["issued_at"] > now
            or p["expires_at"] <= now
            or p["issued_at"] < claims["issued_at"]
            or p["expires_at"] > claims["expires_at"]
            or p["expires_at"] - p["issued_at"] > 300):
        raise AdmissionDenied("RUNTIME_PERMIT_EXPIRED_OR_OUTSIDE_LEASE")
    return {
        "status": "SIGNED_SEPARATE_RUNTIME_PERMIT_ELIGIBLE_NOT_CLAIMED",
        "lease_jti": claims["jti"],
        "head": claims["head"],
        "owner_live_comment_id": owner_live_comment_id,
        "may_access_core": False,
        "may_merge_main": False,
        "may_deploy_production": False,
        "execution_started": False,
    }
