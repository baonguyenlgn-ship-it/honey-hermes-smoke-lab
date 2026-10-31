"""One GitHub-push-woken, read-only TEST mission receiver and receipt.

A successful run proves actual feature-branch push event delivery. It does NOT
prove Owner issue-comment wake, authenticated external callback, signed worker
authority, durable source broker, or unattended live model execution.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

REPO="baonguyenlgn-ship-it/honey-hermes-smoke-lab"
BRANCH="hermes-lab/e2-event-wake-callback-20261101"
MISSION_FILE="hermes_lab_missions/E2-LAB-AUTO-WAKE-01.json"
TASK="HERMES-E2-EVENT-WAKE-READONLY-01"
D_EVIDENCE=41216407415
E1_EVIDENCE=41220878044
REQUIRED_MISSION={
    "schema":"honey.hermes.e2.fixed-readonly-test-mission.v1",
    "task_id":TASK,
    "allowed_scope":"READ_ONLY_LAB_EVENT_RECEIPT",
    "origin":"OWNER_CURRENT_CHAT_TEST_MANDATE",
    "approved_for_model_execution":False,
    "may_publish_code":False,
    "may_access_core":False,
    "may_merge_main":False,
    "may_deploy_production":False,
    "may_spend":False,
    "source_e1_verified_run":E1_EVIDENCE,
    "predecessor_d_verified_run":D_EVIDENCE,
    "next_safe_step":"WRITE_READ_ONLY_ARTIFACT_RECEIPT",
}

class E2Denied(RuntimeError):
    pass

def classify_event(event: dict, mission: dict, *, sha: str, event_kind: str) -> dict:
    if (not isinstance(event,dict)
            or event_kind!="push"
            or event.get("ref")!="refs/heads/"+BRANCH
            or event.get("repository",{}).get("full_name")!=REPO
            or event.get("deleted") is not False
            or event.get("forced") is not False
            or event.get("after")!=sha
            or not isinstance(event.get("before"),str)
            or event["before"]==sha
            or not isinstance(event.get("head_commit"),dict)):
        raise E2Denied("UNTRUSTED_OR_REPLAYED_GITHUB_PUSH_EVENT")
    head=event["head_commit"]
    if MISSION_FILE not in head.get("added",[]) and MISSION_FILE not in head.get("modified",[]):
        raise E2Denied("E2_MISSION_NOT_CHANGED_BY_EVENT")
    if not isinstance(mission,dict) or mission!=REQUIRED_MISSION:
        raise E2Denied("UNTRUSTED_OR_PRIVILEGED_MISSION")
    return {
        "schema":"honey.hermes.e2.push-wake-readonly-receipt.v1",
        "task_id":TASK,
        "event_type":"push",
        "repo":REPO,"branch":BRANCH,"mission_file":MISSION_FILE,
        "push_commit":sha,
        "event_after_matches_commit":True,
        "mission_sha256":hashlib.sha256(
            (json.dumps(mission,sort_keys=True,separators=(",",":"))).encode()
        ).hexdigest(),
        "status":"READ_ONLY_LAB_GITHUB_PUSH_EVENT_VERIFIED",
        "effects_executed":False,
        "real_model_launched":False,
        "external_callback_delivered":False,
        "signed_gate_b_runtime_permit":False,
        "production_authorized":False,
        "durable_external_cas_claim":False,
    }

def main():
    if (os.environ.get("GITHUB_REPOSITORY")!=REPO
            or os.environ.get("GITHUB_REF")!="refs/heads/"+BRANCH
            or not os.environ.get("GITHUB_RUN_ID")):
        raise E2Denied("WRONG_GITHUB_RUNTIME_SCOPE")
    env_path=Path(os.environ["GITHUB_EVENT_PATH"])
    if not env_path.is_file() or env_path.stat().st_size>1000000:
        raise E2Denied("UNTRUSTED_EVENT_FILE")
    event=json.loads(env_path.read_text(encoding="utf-8"))
    mission_path=Path(MISSION_FILE)
    if not mission_path.is_file() or mission_path.stat().st_size>4096:
        raise E2Denied("MISSING_FIXED_MISSION_FILE")
    mission=json.loads(mission_path.read_text(encoding="utf-8"))
    receipt=classify_event(event,mission,sha=os.environ["GITHUB_SHA"],
                            event_kind=os.environ["GITHUB_EVENT_NAME"])
    receipt["github_run_id"]=int(os.environ["GITHUB_RUN_ID"])
    out=Path(os.environ["RUNNER_TEMP"])/"e2-event-receipt"
    out.mkdir(mode=0o700,exist_ok=False)
    (out/"receipt.json").write_text(json.dumps(receipt,sort_keys=True)+"\n",encoding="utf-8")
    print("HERMES_E2_REAL_GITHUB_PUSH_WAKE_VERIFIED_RECEIPT_CREATED",flush=True)
    print("HERMES_E2_SIGNED_LIVE_RUNTIME=False",flush=True)
    print("HERMES_E2_EXTERNAL_CALLBACK_DELIVERED=False",flush=True)

if __name__=="__main__":
    main()
