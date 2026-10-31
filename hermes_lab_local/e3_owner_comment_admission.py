"""E3 read-only intake: verify an actual Owner GitHub PR comment.

This is NOT a remote worker, credential issuer, lease, signed runtime permit,
model executor, authorized callback, or idempotent CAS ledger.
The default-branch issue_comment workflow must be independently reviewed and
merged via standard project governance before any live wake is claimed.
"""
from __future__ import annotations
import hashlib
import json
import os
import urllib.request
from pathlib import Path

REPO="baonguyenlgn-ship-it/honey-hermes-smoke-lab"
OWNER_LOGIN="baonguyenlgn-ship-it"
PR_NUMBER=4
EXPECTED_HEAD="c09fd10fece3a13a2db01a676b0ebc0bb3b3c1c8"
COMMAND="Honey tiếp tục Hermes"
AUDIENCE="honey.hermes.e3.owner-comment-readonly-v1"
MAX_EVENT_BYTES=1000000
MAX_API_BYTES=65536

class AdmissionDenied(RuntimeError):
    pass

def _get_github_json(path: str) -> dict:
    url="https://api.github.com/repos/"+REPO+"/"+path
    req=urllib.request.Request(url,method="GET",headers={
        "Accept":"application/vnd.github+json",
        "User-Agent":"honey-hermes-e3-exact-owner-comment-verify",
    })
    try:
        with urllib.request.urlopen(req,timeout=12) as response:
            if response.status!=200 or response.geturl()!=url:
                raise AdmissionDenied("E3_UNTRUSTED_REMOTE_REDIRECT")
            raw=response.read(MAX_API_BYTES+1)
        if len(raw)>MAX_API_BYTES:
            raise AdmissionDenied("E3_REMOTE_OVERSIZE")
        data=json.loads(raw)
        if not isinstance(data,dict):
            raise AdmissionDenied("E3_REMOTE_SHAPE_INVALID")
        return data
    except (ValueError,OSError):
        raise AdmissionDenied("E3_REMOTE_READBACK_UNAVAILABLE") from None

def verify_owner_comment(event: dict, actual_comment: dict, pr: dict, *,
                         event_type: str, event_action: str) -> dict:
    if (event_type!="issue_comment" or event_action!="created"
            or not isinstance(event,dict)
            or event.get("action")!="created"
            or event.get("repository",{}).get("full_name")!=REPO
            or event.get("repository",{}).get("default_branch")!="main"):
        raise AdmissionDenied("E3_WRONG_EVENT_REPO_OR_ACTION")
    issue=event.get("issue")
    comment=event.get("comment")
    if (not isinstance(issue,dict) or issue.get("number")!=PR_NUMBER
            or not isinstance(issue.get("pull_request"),dict)
            or not isinstance(comment,dict)
            or type(comment.get("id")) is not int
            or comment["id"]<=0):
        raise AdmissionDenied("E3_WRONG_PR_OR_COMMENT_EVENT")
    if (not isinstance(actual_comment,dict)
            or actual_comment.get("id")!=comment["id"]
            or actual_comment.get("body")!=COMMAND
            or comment.get("body")!=COMMAND
            or actual_comment.get("author_association")!="OWNER"
            or comment.get("author_association")!="OWNER"
            or actual_comment.get("user",{}).get("login")!=OWNER_LOGIN
            or actual_comment.get("user",{}).get("type")!="User"
            or comment.get("user",{}).get("login")!=OWNER_LOGIN
            or event.get("sender",{}).get("login")!=OWNER_LOGIN
            or actual_comment.get("created_at")!=actual_comment.get("updated_at")
            or actual_comment.get("created_at")!=comment.get("created_at")):
        raise AdmissionDenied("E3_OWNER_COMMENT_LIVE_IDENTITY_UNVERIFIED")
    if (not isinstance(pr,dict)
            or pr.get("number")!=PR_NUMBER
            or pr.get("state")!="open"
            or pr.get("head",{}).get("sha")!=EXPECTED_HEAD
            or pr.get("head",{}).get("ref")!="hermes-lab/actions-publisher-20261029-01"
            or pr.get("base",{}).get("ref")!="main"
            or pr.get("base",{}).get("repo",{}).get("full_name")!=REPO):
        raise AdmissionDenied("E3_PINNED_PR_HEAD_CHANGED")
    return {
        "aud":AUDIENCE,
        "status":"AUTHENTICATED_OWNER_READONLY_INTENT_NOT_EXECUTED",
        "comment_id":comment["id"],
        "owner_login":OWNER_LOGIN,
        "repo":REPO,
        "pr":PR_NUMBER,
        "pr_head":EXPECTED_HEAD,
        "command_sha256":hashlib.sha256(COMMAND.encode("utf8")).hexdigest(),
        "execution_authorized":False,
        "runtime_permit_issued":False,
        "model_started":False,
        "broker_dispatched":False,
        "callback_sent":False,
        "durable_cas_claimed":False,
        "owner_action_required_for_live_runtime":True,
    }

def main() -> None:
    if (os.environ.get("GITHUB_EVENT_NAME")!="issue_comment"
            or os.environ.get("GITHUB_REPOSITORY")!=REPO
            or not os.environ.get("GITHUB_RUN_ID")):
        raise AdmissionDenied("E3_WRONG_GITHUB_RUNTIME_CONTEXT")
    file=Path(os.environ["GITHUB_EVENT_PATH"])
    if not file.is_file() or file.stat().st_size>MAX_EVENT_BYTES:
        raise AdmissionDenied("E3_EVENT_NOT_PRESENT")
    event=json.loads(file.read_text(encoding="utf8"))
    comment_id=event.get("comment",{}).get("id")
    if type(comment_id) is not int or comment_id<=0:
        raise AdmissionDenied("E3_COMMENT_ID_INVALID")
    authoritative=_get_github_json("issues/comments/"+str(comment_id))
    pr=_get_github_json("pulls/"+str(PR_NUMBER))
    result=verify_owner_comment(event,authoritative,pr,
        event_type="issue_comment",event_action=event.get("action"))
    result["github_run_id"]=int(os.environ["GITHUB_RUN_ID"])
    output=Path(os.environ["RUNNER_TEMP"])/"e3-owner-comment-readonly"
    output.mkdir(mode=0o700,exist_ok=False)
    (output/"receipt.json").write_text(
        json.dumps(result,sort_keys=True)+"\n",encoding="utf8")
    print("HERMES_E3_OWNER_INTENT_READONLY_VERIFIED_NOT_EXECUTED")

if __name__=="__main__":
    main()
