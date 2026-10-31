"""Only NEW E2 event-scope/privilege-negative tests. No model/writer."""
import copy
import unittest
from hermes_lab_local.e2_event_wake import (
    REPO,BRANCH,MISSION_FILE,TASK,REQUIRED_MISSION,E2Denied,classify_event,
)

SHA="a"*40
BASE={
    "ref":"refs/heads/"+BRANCH,
    "repository":{"full_name":REPO},
    "deleted":False,"forced":False,
    "before":"b"*40,"after":SHA,
    "head_commit":{"added":[MISSION_FILE],"modified":[]},
}

PROOF={"sha":SHA,"parents":[{"sha":"b"*40}],
       "files":[{"filename":MISSION_FILE,"status":"added"}]}

class E2EventScopeTests(unittest.TestCase):
    def test_real_shape_of_new_mission_event_passes_only_as_readonly(self):
        r=classify_event(copy.deepcopy(BASE),copy.deepcopy(REQUIRED_MISSION),
                         sha=SHA,event_kind="push",verified_commit=copy.deepcopy(PROOF))
        self.assertEqual(r["status"],"READ_ONLY_LAB_GITHUB_PUSH_EVENT_VERIFIED")
        self.assertEqual(r["task_id"],TASK)
        self.assertFalse(r["real_model_launched"])
        self.assertFalse(r["external_callback_delivered"])
        self.assertFalse(r["durable_external_cas_claim"])

    def test_other_branch_not_eligible(self):
        a=copy.deepcopy(BASE);a["ref"]="refs/heads/main"
        with self.assertRaises(E2Denied):classify_event(a,REQUIRED_MISSION,sha=SHA,event_kind="push",verified_commit=copy.deepcopy(PROOF))

    def test_other_event_not_eligible(self):
        with self.assertRaises(E2Denied):classify_event(BASE,REQUIRED_MISSION,sha=SHA,event_kind="issue_comment",verified_commit=copy.deepcopy(PROOF))

    def test_wrong_repo_not_eligible(self):
        a=copy.deepcopy(BASE);a["repository"]["full_name"]="other/repo"
        with self.assertRaises(E2Denied):classify_event(a,REQUIRED_MISSION,sha=SHA,event_kind="push",verified_commit=copy.deepcopy(PROOF))

    def test_replayed_sha_denied(self):
        a=copy.deepcopy(BASE);a["before"]=SHA
        with self.assertRaises(E2Denied):classify_event(a,REQUIRED_MISSION,sha=SHA,event_kind="push",verified_commit=copy.deepcopy(PROOF))

    def test_force_push_denied(self):
        a=copy.deepcopy(BASE);a["forced"]=True
        with self.assertRaises(E2Denied):classify_event(a,REQUIRED_MISSION,sha=SHA,event_kind="push",verified_commit=copy.deepcopy(PROOF))

    def test_no_mission_delta_denied(self):
        a=copy.deepcopy(BASE);a["head_commit"]["added"]=[];a["head_commit"]["modified"]=[]
        with self.assertRaises(E2Denied):classify_event(a,REQUIRED_MISSION,sha=SHA,event_kind="push",verified_commit=copy.deepcopy(PROOF))

    def test_mission_live_model_flag_denied(self):
        x=dict(REQUIRED_MISSION,approved_for_model_execution=True)
        with self.assertRaises(E2Denied):classify_event(BASE,x,sha=SHA,event_kind="push",verified_commit=copy.deepcopy(PROOF))

    def test_unsafe_next_step_denied(self):
        x=dict(REQUIRED_MISSION,next_safe_step="DISPATCH_ANY_GITHUB_JOB")
        with self.assertRaises(E2Denied):classify_event(BASE,x,sha=SHA,event_kind="push",verified_commit=copy.deepcopy(PROOF))

    def test_paid_or_production_flag_denied(self):
        for key in ("may_spend","may_merge_main","may_deploy_production","may_publish_code","may_access_core"):
            with self.subTest(flag=key):
                x=dict(REQUIRED_MISSION)
                x[key]=True
                with self.assertRaises(E2Denied):classify_event(BASE,x,sha=SHA,event_kind="push",verified_commit=copy.deepcopy(PROOF))

    def test_real_commit_delta_required_not_payload_claim(self):
        a=copy.deepcopy(BASE)
        a["head_commit"]["added"]=[MISSION_FILE]
        p=copy.deepcopy(PROOF);p["files"]=[]
        with self.assertRaises(E2Denied):
            classify_event(a,REQUIRED_MISSION,sha=SHA,event_kind="push",verified_commit=p)

    def test_commit_parent_must_match_event_before(self):
        p=copy.deepcopy(PROOF);p["parents"][0]["sha"]="c"*40
        with self.assertRaises(E2Denied):
            classify_event(BASE,REQUIRED_MISSION,sha=SHA,event_kind="push",verified_commit=p)

if __name__=="__main__":unittest.main()
