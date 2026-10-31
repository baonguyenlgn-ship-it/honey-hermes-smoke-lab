"""Read-only, finite Hermes LAB owner-approved work discovery.

Only pre-existing, immutable Owner mission comments on PR #4 can be suggested.
Discovery is NEVER a durable dequeue, execution approval, model invocation,
new identity credential, or authorization to discover other repositories.
"""
from __future__ import annotations
import json
import re
import urllib.request
from typing import Mapping

from .mission_inbox import (
    REPO, PR, HEADER, TASK, AdmissionDenied as MissionDenied, parse_comment,
)

BRANCH = "hermes-lab/actions-publisher-20261029-01"
API = f"https://api.github.com/repos/{REPO}"
SHA_RE = re.compile(r"[a-f0-9]{40}\Z")
LIMIT = 100
PAGE_SIZE = 20
MAX_PAGES = LIMIT // PAGE_SIZE
MAX_BYTES = 256000


def _result(status: str, *, comment_id: int | None = None) -> dict:
    out = {
        "schema": "honey.hermes.approved-task-discovery.v1",
        "status": status,
        "execution_authority_granted": False,
        "ledger_claimed": False,
        "model_started": False,
        "next_step": "VERIFY_FRESH_SIGNED_JTI_OWNER_CONSENT_AND_PROTECTED_LEDGER",
    }
    if comment_id is not None:
        out["candidate_comment_id"] = comment_id
    return out


def choose_owner_approved(comments, head: str) -> dict:
    """Choose oldest matching immutable approved mission, not arbitrary work.

    A stale, otherwise valid past mission is ignored; every malformed Owner
    mission forces a stop so it cannot be silently treated as authorized.
    """
    if not isinstance(head, str) or SHA_RE.fullmatch(head) is None:
        return _result("STOP_INVALID_REMOTE_HEAD")
    if not isinstance(comments, list) or len(comments) >= LIMIT:
        return _result("STOP_INCOMPLETE_OR_UNTRUSTED_COMMENT_PAGE")
    good = []
    seen = set()
    for comment in comments:
        if not isinstance(comment, Mapping):
            return _result("STOP_UNTRUSTED_COMMENT")
        body = comment.get("body")
        if not isinstance(body, str) or not body.startswith(HEADER + "\n"):
            continue
        try:
            ticket = parse_comment(comment, head)
        except MissionDenied as exc:
            if str(exc) == "STALE_BRANCH_HEAD":
                # To reject a malformed "stale" comment, still parse it
                # against its own head; this NEVER authorizes current HEAD.
                try:
                    payload = json.loads(body[len(HEADER) + 1:])
                    past_head = payload["expected_head"]
                    parse_comment(comment, past_head)
                except (ValueError, KeyError, TypeError, MissionDenied):
                    return _result("STOP_INVALID_OWNER_MISSION")
                continue
            return _result("STOP_INVALID_OWNER_MISSION")
        cid = ticket["comment_id"]
        if cid in seen or ticket["task_id"] != TASK:
            return _result("STOP_DUPLICATE_OR_UNAPPROVED_MISSION")
        seen.add(cid)
        good.append(cid)
    if not good:
        return _result("WAIT_NEW_OWNER_APPROVED_CURRENT_HEAD_MISSION")
    return _result("CANDIDATE_REQUIRES_INDEPENDENT_LEDGER_ADMISSION", comment_id=min(good))


def _get(url: str, opener=None):
    fixed_urls = {f"{API}/pulls/{PR}"}
    fixed_urls.update(
        f"{API}/issues/{PR}/comments?per_page={PAGE_SIZE}&page={i}"
        for i in range(1, MAX_PAGES + 1)
    )
    if url not in fixed_urls:
        raise ValueError("UNAPPROVED_API_TARGET")
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "honey-hermes-approved-task-readonly/1.0",
    }, method="GET")
    with (opener or urllib.request.urlopen)(req, timeout=8) as response:
        if response.status != 200 or response.geturl() != url:
            raise ValueError("UNTRUSTED_GITHUB_HTTP_RESPONSE")
        raw = response.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError("GITHUB_RESPONSE_TOO_LARGE")
    return json.loads(raw)


def read_only_live_discovery(opener=None) -> dict:
    try:
        pr = _get(f"{API}/pulls/{PR}", opener)
        head = pr["head"]
        if (type(pr["number"]) is not int or pr["number"] != PR
                or pr["state"] != "open" or pr["draft"] is not True
                or head["ref"] != BRANCH or head["repo"]["full_name"] != REPO
                or pr["base"]["repo"]["full_name"] != REPO):
            return _result("STOP_PR_IDENTITY_NOT_VERIFIED")
        live_head = head["sha"]
        comments = []
        for page_index in range(1, MAX_PAGES + 1):
            page = _get(
                f"{API}/issues/{PR}/comments?per_page={PAGE_SIZE}&page={page_index}",
                opener,
            )
            if not isinstance(page, list) or len(page) > PAGE_SIZE:
                return _result("STOP_INCOMPLETE_OR_UNTRUSTED_COMMENT_PAGE")
            comments.extend(page)
            if len(page) < PAGE_SIZE:
                return choose_owner_approved(comments, live_head)
        # Never silently accept a full last page: more comments may exist.
        return _result("STOP_INCOMPLETE_OR_UNTRUSTED_COMMENT_PAGE")
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
        return _result("STOP_GITHUB_READBACK_UNAVAILABLE")


if __name__ == "__main__":
    print(json.dumps(read_only_live_discovery(), sort_keys=True))
