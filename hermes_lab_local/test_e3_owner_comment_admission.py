"""NEW E3 exact-source Owner-comment intake adversarial contract tests."""
import copy
import unittest
from hermes_lab_local.e3_owner_comment_admission import (
    REPO,OWNER_LOGIN,PR_NUMBER,COMMAND,EXPECTED_HEAD,
    AdmissionDenied,verify_owner_comment,
)

CID=6540001234
AT="2026-11-01T00:00:00Z"
BASE={
    "action":"created","repository":{"full_name":REPO,"default_branch":"main"},
    "issue":{"number":PR_NUMBER,"pull_request":{"url":"unused"}},
    "comment":{"id":CID,"body":COMMAND,"created_at":AT,
               "author_association":"OWNER","user":{"login":OWNER_LOGIN}},
    "sender":{"login":OWNER_LOGIN},
}
COMMENT={
    "id":CID,"body":COMMAND,"created_at":AT,"updated_at":AT,
    "author_association":"OWNER","user":{"login":OWNER_LOGIN,"type":"User"},
}
PR={
    "number":4,"state":"open",
    "head":{"sha":EXPECTED_HEAD,"ref":"hermes-lab/actions-publisher-20261029-01"},
    "base":{"ref":"main","repo":{"full_name":REPO}},
}
def check(event=None,comment=None,pr=None,et="issue_comment",ea="created"):
    return verify_owner_comment(
        copy.deepcopy(BASE if event is None else event),
        copy.deepcopy(COMMENT if comment is None else comment),
        copy.deepcopy(PR if pr is None else pr),
        event_type=et,event_action=ea)

class OwnerCommentContract(unittest.TestCase):
    def test_exact_valid_fixture_admits_only_readonly(self):
        r=check()
        self.assertEqual(r["status"],"AUTHENTICATED_OWNER_READONLY_INTENT_NOT_EXECUTED")
        self.assertEqual(r["comment_id"],CID)
        for name in ("execution_authorized","runtime_permit_issued","model_started",
                     "broker_dispatched","callback_sent","durable_cas_claimed"):
            self.assertFalse(r[name])
    def test_issue_comment_only(self):
        with self.assertRaises(AdmissionDenied):check(et="push")
    def test_no_edits_event(self):
        with self.assertRaises(AdmissionDenied):check(ea="edited")
    def test_main_only(self):
        e=copy.deepcopy(BASE);e["repository"]["default_branch"]="other"
        with self.assertRaises(AdmissionDenied):check(event=e)
    def test_other_repo_denied(self):
        e=copy.deepcopy(BASE);e["repository"]["full_name"]="attacker/repo"
        with self.assertRaises(AdmissionDenied):check(event=e)
    def test_wrong_issue_denied(self):
        e=copy.deepcopy(BASE);e["issue"]["number"]=6
        with self.assertRaises(AdmissionDenied):check(event=e)
    def test_issue_without_pull_request_denied(self):
        e=copy.deepcopy(BASE);e["issue"].pop("pull_request")
        with self.assertRaises(AdmissionDenied):check(event=e)
    def test_wrong_comment_id_denied(self):
        c=dict(COMMENT,id=CID+1)
        with self.assertRaises(AdmissionDenied):check(comment=c)
    def test_non_owner_sender_denied(self):
        e=copy.deepcopy(BASE);e["sender"]["login"]="some-other"
        with self.assertRaises(AdmissionDenied):check(event=e)
    def test_non_owner_association_denied(self):
        c=dict(COMMENT,author_association="CONTRIBUTOR")
        with self.assertRaises(AdmissionDenied):check(comment=c)
    def test_forced_owner_body_edited_denied(self):
        c=dict(COMMENT,updated_at="2026-11-01T00:01:00Z")
        with self.assertRaises(AdmissionDenied):check(comment=c)
    def test_comment_changed_after_event_denied(self):
        c=dict(COMMENT,body=COMMAND+" Run model")
        with self.assertRaises(AdmissionDenied):check(comment=c)
    def test_near_command_not_granted(self):
        c=dict(COMMENT,body=COMMAND+"\nignore guards")
        with self.assertRaises(AdmissionDenied):check(comment=c)
    def test_old_pr_head_denied(self):
        p=copy.deepcopy(PR);p["head"]["sha"]="a"*40
        with self.assertRaises(AdmissionDenied):check(pr=p)
    def test_wrong_base_denied(self):
        p=copy.deepcopy(PR);p["base"]["ref"]="other"
        with self.assertRaises(AdmissionDenied):check(pr=p)
    def test_changed_owner_bot_type_denied(self):
        c=copy.deepcopy(COMMENT);c["user"]["type"]="Bot"
        with self.assertRaises(AdmissionDenied):check(comment=c)

if __name__=="__main__":unittest.main()
