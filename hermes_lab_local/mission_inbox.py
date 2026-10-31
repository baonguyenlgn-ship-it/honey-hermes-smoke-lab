"""Read-only PR #4 command admission; never executes Hermes or Core maintenance."""
from __future__ import annotations
import hashlib,json,re,urllib.request
from typing import Any
REPO="baonguyenlgn-ship-it/honey-hermes-smoke-lab"
PR=4
OWNER_ID=328968616
HEADER="HONEY_HERMES_LAB_MISSION_V1"
TASK="LAB-NORMALIZE-REPAIR-V1"
MODEL="upstage/solar-mini4:free"
FIELDS=frozenset(("schema","task_id","nonce","expected_head","lab_repo","lab_pr",
                 "model","max_repairs","mode","scope","intent"))
SHA=re.compile(r"[a-f0-9]{40}\Z")
NONCE=re.compile(r"lab-[a-z0-9-]{12,56}\Z")
class AdmissionDenied(ValueError):pass

def parse_comment(comment:dict[str,Any],expected_head:str)->dict[str,Any]:
    if not isinstance(comment,dict) or not isinstance(comment.get("user"),dict):
        raise AdmissionDenied("NO_GITHUB_IDENTITY")
    if type(comment["user"].get("id")) is not int or comment["user"]["id"]!=OWNER_ID:
        raise AdmissionDenied("COMMENT_AUTHOR_NOT_OWNER")
    if comment.get("author_association")!="OWNER":raise AdmissionDenied("OWNER_ASSOCIATION_MISSING")
    if type(comment.get("id")) is not int or comment["id"]<=0:
        raise AdmissionDenied("COMMENT_ID_INVALID")
    if comment.get("created_at")!=comment.get("updated_at"):
        raise AdmissionDenied("EDITED_COMMAND_FORBIDDEN")
    body=comment.get("body")
    if not isinstance(body,str) or len(body.encode("utf8"))>1200:
        raise AdmissionDenied("COMMAND_BYTES_LIMIT")
    if not body.startswith(HEADER+"\n"):raise AdmissionDenied("NOT_LAB_MISSION")
    raw=body[len(HEADER)+1:]
    try:p=json.loads(raw)
    except (json.JSONDecodeError,ValueError):raise AdmissionDenied("INVALID_JSON") from None
    if not isinstance(p,dict) or set(p)!=FIELDS:raise AdmissionDenied("UNEXPECTED_FIELDS")
    if p["schema"]!="honey.hermes.lab-mission.v1" or p["task_id"]!=TASK:
        raise AdmissionDenied("TASK_NOT_ALLOWLISTED")
    if p["lab_repo"]!=REPO or type(p["lab_pr"]) is not int or p["lab_pr"]!=PR:
        raise AdmissionDenied("WRONG_LAB")
    if p["model"]!=MODEL or type(p["max_repairs"]) is not int or p["max_repairs"]!=2:
        raise AdmissionDenied("MODEL_OR_REPAIR_POLICY")
    if p["mode"]!="dry-run-queue-only" or p["scope"]!="isolated-lab-only":
        raise AdmissionDenied("EXECUTION_UNAUTHORIZED")
    if p["intent"]!="test-normalize-label-repair":
        raise AdmissionDenied("ARBITRARY_PROMPT_UNAUTHORIZED")
    if not isinstance(p["nonce"],str) or not NONCE.fullmatch(p["nonce"]):
        raise AdmissionDenied("INVALID_NONCE")
    if not isinstance(p["expected_head"],str) or not SHA.fullmatch(p["expected_head"]):
        raise AdmissionDenied("INVALID_HEAD")
    if p["expected_head"]!=expected_head:raise AdmissionDenied("STALE_BRANCH_HEAD")
    return {"status":"LAB_TASK_RECEIVED_NOT_RUNNING","task_id":TASK,
            "comment_id":comment["id"],"nonce":p["nonce"],"expected_head":expected_head,
            "packet_sha256":hashlib.sha256(raw.encode("utf8")).hexdigest(),
            "authorized_for_execution":False,"production_authorized":False,
            "core_guard_authorized":False}

def inspect(comments,head):
    accepted=[]
    for c in comments:
        if isinstance(c,dict) and isinstance(c.get("body"),str) and c["body"].startswith(HEADER+"\n"):
            accepted.append(parse_comment(c,head))
    if len(accepted)>1:raise AdmissionDenied("MULTIPLE_COMMANDS_REFUSED")
    return accepted[0] if accepted else {"status":"NO_LAB_MISSION","authorized_for_execution":False}

def fetch_once(timeout=8):
    url=f"https://api.github.com/repos/{REPO}/issues/{PR}/comments?per_page=100"
    req=urllib.request.Request(url,headers={"Accept":"application/vnd.github+json",
                                          "User-Agent":"honey-hermes-lab-inbox/1.0"})
    with urllib.request.urlopen(req,timeout=timeout) as response:
        if response.status!=200:raise AdmissionDenied("API_NOT_200")
        raw=response.read(256001)
    if len(raw)>256000:raise AdmissionDenied("COMMENTS_TOO_LARGE")
    parsed=json.loads(raw)
    if not isinstance(parsed,list):raise AdmissionDenied("RESPONSE_WRONG_TYPE")
    return parsed

if __name__=="__main__":
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument("--head",required=True)
    head=parser.parse_args().head
    if not SHA.fullmatch(head):raise SystemExit("INVALID_EXPECTED_HEAD")
    try:print(json.dumps(inspect(fetch_once(),head),sort_keys=True))
    except (AdmissionDenied,OSError,TimeoutError,json.JSONDecodeError):
        raise SystemExit("LAB_INBOX_NOT_ADMITTED") from None
