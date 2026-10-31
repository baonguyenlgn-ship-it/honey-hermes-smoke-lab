"""One genuinely self-selected NEXT SAFE isolated Hermes LAB coding task.

Verify prior *actual* GitHub Windows AIAgent QA run via live GitHub API and
read the current Owner queue independently; only when no Owner-approved
production/real mission is pending may this path choose the one finite local
LAB-only task. No arbitrary issue execution, Git writer, merged branch,
CodeSpace admission or paid model. Fail closed on any unverified condition.
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
from pathlib import Path
import subprocess
import urllib.request

from .approved_task_discovery import read_only_live_discovery
from .windows_local_hermes_direct_agent import actual_model_turn
from .windows_local_hermes_coding import QaRejected, PINNED_HERMES

REPO = "baonguyenlgn-ship-it/honey-hermes-smoke-lab"
PREVIOUS_RUN_ID = 41209407767
PREVIOUS_HEAD = "b7b0ef96ba6946321efb58516e2cef5ffbec4ec4"
PREVIOUS_WORKFLOW = "Hermes native Windows real AIAgent local model code and QA repair"
BRANCH = "hermes-lab/honey-isolated-gateway-diagnostics-20261031"
PREVIOUS_CODE_SHA256 = "5205373ad9d95c0e1d0c71639fc0f140789c24e1741426f8b89ba8c74f10ad5a"
NEXT_TASK = {
    "id": "HERMES-LOCAL-TEST-IS-LOW-STOCK-01",
    "function": "is_low_stock",
    "status": "PREAPPROVED_ISOLATED_LAB_FIXED_ALLOWLIST_ONLY",
}
EXPECTED = "def is_low_stock(available, minimum):\n    return int(available) < int(minimum)"
CASES = ((0,1,True),(1,0,False),(5,5,False),(3,5,True),
         (-1,0,True),(" 2 ","4",True),(10,7,False))
MAX_REPAIRS = 2

def _fixed_get(url: str) -> dict:
    if url != f"https://api.github.com/repos/{REPO}/actions/runs/{PREVIOUS_RUN_ID}":
        raise RuntimeError("UNTRUSTED_PREDECESSOR_URL")
    req=urllib.request.Request(url,headers={
        "User-Agent":"honey-hermes-real-next-task-readonly/1.0",
        "Accept":"application/vnd.github+json",
    },method="GET")
    with urllib.request.urlopen(req,timeout=10) as res:
        if res.status != 200 or res.geturl() != url:
            raise RuntimeError("UNTRUSTED_RUN_HTTP")
        raw=res.read(65537)
    if len(raw)>65536:
        raise RuntimeError("RUN_METADATA_TOO_LARGE")
    data=json.loads(raw)
    if not isinstance(data,dict):
        raise RuntimeError("UNTRUSTED_RUN_METADATA")
    return data

def check_predecessor_and_owner_queue() -> dict:
    # This is real remote GitHub evidence, not prior model output.
    prior=_fixed_get(f"https://api.github.com/repos/{REPO}/actions/runs/{PREVIOUS_RUN_ID}")
    if (prior.get("id")!=PREVIOUS_RUN_ID
            or prior.get("status")!="completed"
            or prior.get("conclusion")!="success"
            or prior.get("head_sha")!=PREVIOUS_HEAD
            or prior.get("head_branch")!=BRANCH
            or prior.get("name")!=PREVIOUS_WORKFLOW
            or prior.get("event")!="push"
            or prior.get("repository",{}).get("full_name")!=REPO):
        raise RuntimeError("PREDECESSOR_REAL_WINDOWS_PASS_NOT_PROVEN")
    # No model-derived issue selection. Owner mission queue is independently
    # read and any pending execution consent remains separately required.
    queue=read_only_live_discovery()
    if queue.get("status")!="WAIT_NEW_OWNER_APPROVED_CURRENT_HEAD_MISSION":
        raise RuntimeError("OWNER_QUEUE_NOT_CLEAR_FOR_FIXED_LAB_NEXT_TASK")
    if (queue.get("execution_authority_granted") is not False
            or queue.get("model_started") is not False
            or queue.get("ledger_claimed") is not False):
        raise RuntimeError("OWNER_QUEUE_PRIVILEGE_STATE_UNTRUSTED")
    return {"predecessor_run":PREVIOUS_RUN_ID,
            "current_owner_queue":queue["status"],
            "scope":"fixed-isolated-no-github-writes"}

def qa_new_task(source: str) -> bytes:
    if not isinstance(source,str):
        raise QaRejected("NOT_TEXT")
    raw=source.encode("utf8")
    if not (35<=len(raw)<=2048) or any(z in source for z in ("\x00","\r","\ufeff")):
        raise QaRejected("SOURCE_BYTES_INVALID")
    try: tree=ast.parse(source)
    except (SyntaxError,ValueError):raise QaRejected("PYTHON_SYNTAX_INVALID") from None
    if ast.dump(tree,include_attributes=False)!=ast.dump(ast.parse(EXPECTED),include_attributes=False):
        raise QaRejected("SAFE_AST_NOT_MATCHED")
    env={"__builtins__":{"int":int}}
    exec(compile(tree,"<hermes-real-new-task-qa>","exec"),env)
    for qty,minimum,expected in CASES:
        if env["is_low_stock"](qty,minimum) is not expected:
            raise QaRejected("BEHAVIOR_MISMATCH")
    return raw

def main():
    evidence=check_predecessor_and_owner_queue()
    print("HERMES_AUTOMATIC_NEXT_LAB_TASK_LIVE_GITHUB_PREDECESSOR_PASS_VERIFIED",flush=True)
    print("HERMES_AUTOMATIC_NEXT_OWNER_QUEUE="+evidence["current_owner_queue"],flush=True)
    # Only one fixed, non-customer, nonproduction task is admitted.
    print("HERMES_AUTOMATIC_NEXT_LAB_TASK_SELECTED="+NEXT_TASK["id"],flush=True)
    source=Path(os.environ["HERMES_UPSTREAM_SOURCE"]).resolve()
    if subprocess.check_output(["git","-C",str(source),"rev-parse","HEAD"],
                               text=True).strip()!=PINNED_HERMES:
        raise RuntimeError("UPSTREAM_PIN_CHANGED")
    temporary=Path(os.environ["RUNNER_TEMP"]).resolve()/"hermes-automatic-next"
    temporary.mkdir(mode=0o700,exist_ok=False)
    prompt=(
        "Write ONLY Python source, no Markdown or commentary, defining exactly "
        "one function named is_low_stock(available, minimum). Convert each "
        "argument to int and return True strictly when available is below "
        "minimum, otherwise False. No imports or extra functions."
    )
    for attempt in range(MAX_REPAIRS+1):
        print("HERMES_AUTOMATIC_NEXT_REAL_MODEL_ATTEMPT="+str(attempt+1),flush=True)
        source_code=actual_model_turn(prompt,attempt,source,temporary)
        try: checked=qa_new_task(source_code)
        except QaRejected as error:
            code=str(error)
            print("HERMES_AUTOMATIC_NEXT_REAL_QA_REJECTED="+code,flush=True)
            if attempt==MAX_REPAIRS:
                raise RuntimeError("NEXT_LAB_TASK_REPAIR_LIMIT_EXHAUSTED")
            prompt=(
                "Independent QA rejected your previous Python answer: "+code+
                ". Repair and output ONLY Python source. Define exactly one "
                "function is_low_stock(available, minimum) returning "
                "int(available) < int(minimum). No Markdown, imports or "
                "additional text."
            )
            continue
        print(json.dumps({
            "status":"HERMES_AUTOMATIC_NEXT_FIXED_LAB_TASK_QA_PASS",
            "task_id":NEXT_TASK["id"],
            "after_real_windows_qa_run":PREVIOUS_RUN_ID,
            "predecessor_sha256":PREVIOUS_CODE_SHA256,
            "sha256":hashlib.sha256(checked).hexdigest(),
            "size":len(checked),"attempts":attempt+1,
            "repairs":attempt,"owner_queue":evidence["current_owner_queue"],
            "actual_model":"local-loopback-Qwen2.5Coder1.5b",
            "actual_hermes_upstream_sha":PINNED_HERMES,
            "production_authorized":False,
            "signed_gate_b":False,
            "unattended_github_issue_dispatch":False,
            "github_writes":False,
        },sort_keys=True),flush=True)
        return
    raise RuntimeError("UNREACHABLE_NEXT_TASK")

if __name__=="__main__":
    main()
