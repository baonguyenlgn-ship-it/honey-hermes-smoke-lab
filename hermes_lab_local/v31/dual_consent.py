"""Second authorization gate: immutable Owner LIVE intent + independently signed TEST lease.

The historical LAB mission #6523530512 is explicitly DRY-RUN; it must NEVER be
reinterpreted as permission to execute. Neither a GitHub comment alone nor a
lease alone is execution authority. All readbacks must be independently fetched
from GitHub, not pasted by the model. This module executes NOTHING.
"""
from __future__ import annotations

import json
import re
from typing import Mapping

from .one_use_lease_gate import (
    AdmissionDenied, BRANCH, MODEL, REPO, TASK, TrustedHostContext,
    claim_once, verify_signed_lease,
)

OWNER_ID = 328968616
LEGACY_MISSION_ID = 6523530512
EXPECTED_ISSUE_URL = f"https://api.github.com/repos/{REPO}/issues/4"
HEADER = "HONEY_HERMES_LAB_LIVE_CONSENT_V1"
SCHEMA = "honey.hermes.lab-live-consent.v1"
LIVE_KEYS = frozenset({
    "schema", "task_id", "repo", "pr", "branch", "head", "model",
    "max_repairs", "legacy_mission_comment_id", "legacy_nonce",
    "lease_jti", "mode", "scope", "intent",
})
SHA_RE = re.compile(r"[a-f0-9]{40}\Z")


def parse_live_owner_comment(comment: Mapping, legacy_ticket: Mapping,
                             signed_claims: Mapping) -> dict:
    """Accept a SECOND genuine, unedited Owner comment, never the dry-run command.

    The lease MUST first have been independently signature-verified against a
    trusted host context; arbitrary caller-provided 'claims' are not trusted.
    """
    if not isinstance(comment, dict) or not isinstance(comment.get("user"), dict):
        raise AdmissionDenied("OWNER_LIVE_COMMENT_NOT_PROVEN")
    if (type(comment["user"].get("id")) is not int
            or comment["user"]["id"] != OWNER_ID
            or comment.get("author_association") != "OWNER"
            or type(comment.get("id")) is not int
            or comment["id"] <= 0
            or comment["id"] == LEGACY_MISSION_ID
            or comment.get("issue_url") != EXPECTED_ISSUE_URL
            or not isinstance(comment.get("created_at"), str)
            or comment.get("created_at") != comment.get("updated_at")):
        raise AdmissionDenied("NOT_AN_IMMUTABLE_SEPARATE_OWNER_APPROVAL")
    body = comment.get("body")
    if not isinstance(body, str) or len(body.encode("utf-8")) > 1200:
        raise AdmissionDenied("OWNER_LIVE_COMMENT_SIZE_INVALID")
    if not body.startswith(HEADER + "\n"):
        raise AdmissionDenied("NO_OWNER_LIVE_EXECUTION_INTENT")
    try:
        payload = json.loads(body[len(HEADER)+1:])
    except (ValueError, TypeError):
        raise AdmissionDenied("INVALID_OWNER_LIVE_PAYLOAD") from None
    if not isinstance(payload, dict) or set(payload) != LIVE_KEYS:
        raise AdmissionDenied("OWNER_LIVE_FIELDS_NOT_ALLOWLISTED")
    if (payload["schema"] != SCHEMA
            or payload["task_id"] != TASK
            or payload["repo"] != REPO
            or type(payload["pr"]) is not int or payload["pr"] != 4
            or payload["branch"] != BRANCH
            or not isinstance(payload["head"], str)
            or not SHA_RE.fullmatch(payload["head"])
            or payload["head"] != signed_claims["head"]
            or payload["model"] != MODEL
            or type(payload["max_repairs"]) is not int
            or payload["max_repairs"] != 2
            or payload["mode"] != "lab-execute-once"
            or payload["scope"] != "isolated-lab-only"
            or payload["intent"] != "test-normalize-label-repair"
            or type(payload["legacy_mission_comment_id"]) is not int
            or payload["legacy_mission_comment_id"] != LEGACY_MISSION_ID
            or payload["legacy_mission_comment_id"] != legacy_ticket["comment_id"]
            or payload["legacy_nonce"] != legacy_ticket["nonce"]
            or payload["lease_jti"] != signed_claims["jti"]):
        raise AdmissionDenied("OWNER_LIVE_SCOPE_OR_LEASE_MISMATCH")
    return {"status": "OWNER_LIVE_INTENT_VALIDATED_NOT_EXECUTED",
            "owner_live_comment_id": comment["id"],
            "lease_jti": payload["lease_jti"], "head": payload["head"],
            "permitted_to_execute": False, "permitted_to_publish": False}


def verify_dual_consent(signed_bundle: Mapping, legacy_ticket: Mapping,
                        live_comment: Mapping, host: TrustedHostContext,
                        *, now: int | None = None) -> dict:
    """Read-only dual consent: verifies test issuer + separate live Owner intent.

    Legacy dry-run command without this second comment is ALWAYS rejected.
    """
    signed_claims = verify_signed_lease(signed_bundle, legacy_ticket, host, now=now)
    if live_comment is None:
        raise AdmissionDenied("LIVE_OWNER_EXECUTION_CONSENT_MISSING")
    return parse_live_owner_comment(live_comment, legacy_ticket, signed_claims)


def claim_dual_consent_once(signed_bundle: Mapping, legacy_ticket: Mapping,
                            live_comment: Mapping, host: TrustedHostContext,
                            *, now: int | None = None) -> dict:
    """Only CLAIM once after dual consent. No worker/broker/model invocation.

    Host operator must independently check host/fencing/revocation/cost policy,
    reconcile fresh PR HEAD, and authorize runtime separately.
    """
    consent = verify_dual_consent(signed_bundle, legacy_ticket, live_comment,
                                  host, now=now)
    claim = claim_once(signed_bundle, legacy_ticket, host, now=now)
    claim["owner_live_comment_id"] = consent["owner_live_comment_id"]
    claim["dual_consent_validated"] = True
    claim["permitted_to_execute"] = False
    return claim
