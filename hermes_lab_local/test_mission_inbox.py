"""Synthetic command intake fixtures only. No Hermes provider inference."""
import json,unittest
from copy import deepcopy
from hermes_lab_local.mission_inbox import HEADER,OWNER_ID,REPO,PR,MODEL,AdmissionDenied,parse_comment,inspect
HEAD="a"*40
PACKET={"schema":"honey.hermes.lab-mission.v1","task_id":"LAB-NORMALIZE-REPAIR-V1",
"nonce":"lab-test-command-20261030","expected_head":HEAD,
"lab_repo":REPO,"lab_pr":PR,"model":MODEL,"max_repairs":2,
"mode":"dry-run-queue-only","scope":"isolated-lab-only","intent":"test-normalize-label-repair"}
def sample(p=None):
    return {"id":123456,"user":{"id":OWNER_ID},"author_association":"OWNER",
            "created_at":"2026-10-30T10:00:00Z","updated_at":"2026-10-30T10:00:00Z",
            "body":HEADER+"\n"+json.dumps(PACKET if p is None else p)}
class AdmissionSecurity(unittest.TestCase):
    def test_one_verified_owner_command_queued_not_run(self):
        x=inspect([sample()],HEAD)
        self.assertEqual(x["status"],"LAB_TASK_RECEIVED_NOT_RUNNING")
        self.assertIs(x["authorized_for_execution"],False)
        self.assertIs(x["core_guard_authorized"],False)
    def test_empty(self):self.assertEqual(inspect([],HEAD)["status"],"NO_LAB_MISSION")
    def test_owner_id(self):
        c=sample();c["user"]["id"]=500
        with self.assertRaises(AdmissionDenied):parse_comment(c,HEAD)
    def test_owner_association(self):
        c=sample();c["author_association"]="CONTRIBUTOR"
        with self.assertRaises(AdmissionDenied):parse_comment(c,HEAD)
    def test_edit_rejected(self):
        c=sample();c["updated_at"]="2026-10-30T10:00:01Z"
        with self.assertRaises(AdmissionDenied):parse_comment(c,HEAD)
    def test_nonce(self):
        p=deepcopy(PACKET);p["nonce"]="../../x"
        with self.assertRaises(AdmissionDenied):parse_comment(sample(p),HEAD)
    def test_stale_head(self):
        with self.assertRaises(AdmissionDenied):parse_comment(sample(),"b"*40)
    def test_wrong_pr(self):
        p=deepcopy(PACKET);p["lab_pr"]=266
        with self.assertRaises(AdmissionDenied):parse_comment(sample(p),HEAD)
    def test_no_b07_command(self):
        p=deepcopy(PACKET);p["intent"]="unlock-B07-B08-B09-B10-root"
        with self.assertRaises(AdmissionDenied):parse_comment(sample(p),HEAD)
    def test_no_paid_provider(self):
        p=deepcopy(PACKET);p["model"]="paid"
        with self.assertRaises(AdmissionDenied):parse_comment(sample(p),HEAD)
    def test_no_third_repair(self):
        p=deepcopy(PACKET);p["max_repairs"]=3
        with self.assertRaises(AdmissionDenied):parse_comment(sample(p),HEAD)
    def test_no_exec_mode(self):
        p=deepcopy(PACKET);p["mode"]="execute-now"
        with self.assertRaises(AdmissionDenied):parse_comment(sample(p),HEAD)
    def test_no_extra_fields(self):
        p=deepcopy(PACKET);p["root"]=True
        with self.assertRaises(AdmissionDenied):parse_comment(sample(p),HEAD)
    def test_duplicate_refused(self):
        with self.assertRaises(AdmissionDenied):inspect([sample(),sample()],HEAD)
    def test_overlong_body(self):
        c=sample();c["body"]+="x"*2000
        with self.assertRaises(AdmissionDenied):parse_comment(c,HEAD)
    def test_no_plain_comment(self):
        c=sample();c["body"]="Honey please deploy main"
        self.assertEqual(inspect([c],HEAD)["status"],"NO_LAB_MISSION")
