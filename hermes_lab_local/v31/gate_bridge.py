"""Read-only LAB command → authenticated TEST lease admission bridge.

Intended to run INSIDE the existing Hermes LAB only after an independent host
custodian has pinned a legitimate Ed25519 public key and protected ledger.
Do not install/use as a live runner solely because it exists in an archive.
This module never invokes a model, broker, or GitHub write endpoint.
"""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from typing import Mapping

from .dual_consent import claim_dual_consent_once, EXPECTED_ISSUE_URL, LEGACY_MISSION_ID

from .one_use_lease_gate import (
    AdmissionDenied, TrustedHostContext, REPO, BRANCH, TASK,
    verify_signed_lease,
)

PR_NO = 4
OWNER_MISSION_COMMENT_ID = 6523530512
GITHUB_API = f"https://api.github.com/repos/{REPO}"
ACCEPTED_PR_KEYS = ("number", "state", "draft", "head", "base")
MAX_BODY = 1200


def verify_pr_snapshot(pr: Mapping, *, expected_head: str) -> str:
    """Check independently fetched API PR metadata, NOT user-supplied text."""
    if not isinstance(pr, dict) or not all(k in pr for k in ACCEPTED_PR_KEYS):
        raise AdmissionDenied("PR_SNAPSHOT_MISSING")
    head = pr["head"]
    base = pr["base"]
    if not isinstance(head, dict) or not isinstance(base, dict):
        raise AdmissionDenied("PR_REFS_MISSING")
    headrepo, baserepo = head.get("repo"), base.get("repo")
    if not isinstance(headrepo, dict) or not isinstance(baserepo, dict):
        raise AdmissionDenied("PR_REPOS_MISSING")
    # Untrusted API payloads must fail closed with a stable AdmissionDenied,
    # even when an expected nested key is omitted or has an unexpected type.
    if (type(pr["number"]) is not int or pr["number"] != PR_NO
            or pr["state"] != "open" or pr["draft"] is not True
            or head.get("ref") != BRANCH
            or headrepo.get("full_name") != REPO
            or baserepo.get("full_name") != REPO
            or head.get("sha") != expected_head
            or not isinstance(expected_head, str)
            or not re.fullmatch(r"[0-9a-f]{40}", expected_head)):
        raise AdmissionDenied("PR_BRANCH_OR_SHA_MISMATCH")
    return expected_head


def _http_json(url: str, *, limit: int = 131072, opener=None,
               live_comment_id: int | None = None) -> dict:
    """Strict bounded PUBLIC GitHub GET; no PAT, no dynamic external target."""
    allowed = {
        f"{GITHUB_API}/pulls/{PR_NO}",
        f"{GITHUB_API}/issues/comments/{OWNER_MISSION_COMMENT_ID}",
    }
    if type(live_comment_id) is int and live_comment_id > 0 and live_comment_id != LEGACY_MISSION_ID:
        allowed.add(f"{GITHUB_API}/issues/comments/{live_comment_id}")
    if not url.startswith(GITHUB_API + "/") or url not in allowed:
        raise AdmissionDenied("URL_NOT_ALLOWLISTED")
    request = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "honey-hermes-lab-gate-readonly/1.0",
    }, method="GET")
    try:
        response = (opener or urllib.request.urlopen)(request, timeout=8)
        with response:
            if response.status != 200 or response.geturl() != url:
                raise AdmissionDenied("GITHUB_API_RESPONSE_NOT_TRUSTED")
            blob = response.read(limit + 1)
        if len(blob) > limit:
            raise AdmissionDenied("GITHUB_RESPONSE_TOO_LARGE")
        data = json.loads(blob)
        if not isinstance(data, dict):
            raise AdmissionDenied("GITHUB_RESPONSE_NOT_OBJECT")
        return data
    except (urllib.error.URLError, TimeoutError, OSError, ValueError,
            UnicodeDecodeError, json.JSONDecodeError) as exc:
        if isinstance(exc, AdmissionDenied):
            raise
        raise AdmissionDenied("GITHUB_READBACK_FAILED") from None


def fetch_snapshot(*, opener=None):
    """Read only the one existing PR and the one existing Owner mission."""
    pr = _http_json(f"{GITHUB_API}/pulls/{PR_NO}", opener=opener)
    comment = _http_json(
        f"{GITHUB_API}/issues/comments/{OWNER_MISSION_COMMENT_ID}",
        limit=16384, opener=opener,
    )
    if type(comment.get("id")) is not int or comment["id"] != OWNER_MISSION_COMMENT_ID:
        raise AdmissionDenied("WRONG_MISSION_COMMENT_ID")
    if not isinstance(comment.get("body"), str) or len(comment["body"].encode()) > MAX_BODY:
        raise AdmissionDenied("MISSION_BODY_LIMIT")
    return pr, comment


def fetch_live_consent(comment_id: int, *, opener=None) -> dict:
    """Independently read the *second* Owner comment by exact GitHub ID.

    A current PR comment list alone is not an execution authorization.
    Caller must use verify_dual_consent with externally pinned lease after read.
    """
    if type(comment_id) is not int or comment_id <= 0 or comment_id == LEGACY_MISSION_ID:
        raise AdmissionDenied("INVALID_LIVE_COMMENT_ID")
    comment = _http_json(f"{GITHUB_API}/issues/comments/{comment_id}",
                         limit=16384, opener=opener, live_comment_id=comment_id)
    if (type(comment.get("id")) is not int or comment["id"] != comment_id
            or comment.get("issue_url") != EXPECTED_ISSUE_URL
            or not isinstance(comment.get("body"), str)
            or len(comment["body"].encode("utf8")) > MAX_BODY):
        raise AdmissionDenied("LIVE_COMMENT_NOT_FROM_OWNED_PR")
    return comment


def verify_original_inbox_ticket(comment, expected_head):
    """Reuse actual mission_inbox parser on exact upstream branch; no duplication.

    Import fails closed unless the existing LAB source is installed. Upstream
    checks GitHub Owner ID, immutable comment, schema/nonce, dry-run task model.
    """
    try:
        from hermes_lab_local.mission_inbox import parse_comment
        ticket = parse_comment(comment, expected_head)
    except (ImportError, ValueError, KeyError, TypeError) as exc:
        raise AdmissionDenied("UPSTREAM_INBOX_REJECTED") from None
    if (ticket.get("comment_id") != OWNER_MISSION_COMMENT_ID
            or ticket.get("task_id") != TASK
            or ticket.get("status") != "LAB_TASK_RECEIVED_NOT_RUNNING"):
        raise AdmissionDenied("UNEXPECTED_UPSTREAM_TICKET")
    return ticket


def preflight_readonly(pr, comment, signed_bundle, host: TrustedHostContext, *, now=None):
    """Verify all facts, deliberately with ZERO admission/ledger/worker side effects."""
    if not isinstance(signed_bundle, dict) or not isinstance(signed_bundle.get("claims"), dict):
        raise AdmissionDenied("NO_EXTERNAL_SIGNED_LEASE")
    expected_head = signed_bundle["claims"].get("head")
    verify_pr_snapshot(pr, expected_head=expected_head)
    ticket = verify_original_inbox_ticket(comment, expected_head)
    return verify_signed_lease(signed_bundle, ticket, host, now=now)


def claim_from_readback(pr, comment, pr_again, signed_bundle,
                        host: TrustedHostContext, *, live_comment=None, now=None):
    """One-use admission only with a *separate Owner LIVE consent comment*.

    The legacy DRY-RUN comment must never be escalated by this bridge.
    Repeat PR readback prevents obvious pre-claim drift.

    The execution broker MUST still perform a CAS immediately at publication.
    This function is *not* an execution lease by itself and starts no worker.
    """
    preflight_readonly(pr, comment, signed_bundle, host, now=now)
    verify_pr_snapshot(pr_again, expected_head=signed_bundle["claims"]["head"])
    ticket = verify_original_inbox_ticket(comment, signed_bundle["claims"]["head"])
    return claim_dual_consent_once(signed_bundle, ticket, live_comment, host, now=now)
