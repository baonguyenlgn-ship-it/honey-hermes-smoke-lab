"""Only NEW read-only owner-mission-discovery cases; no model, signer or dispatch."""
import json
import unittest
from unittest.mock import Mock

from hermes_lab_local.approved_task_discovery import (
    choose_owner_approved, read_only_live_discovery, BRANCH, REPO, PR,
)
from hermes_lab_local.mission_inbox import HEADER, OWNER_ID, TASK, MODEL

HEAD = "a" * 40
PAST = "b" * 40


def ticket(head=HEAD, *, cid=17, owner=OWNER_ID, **replacements):
    data = dict(schema="honey.hermes.lab-mission.v1", task_id=TASK,
        nonce="lab-inbox-owner-demo-20261030", expected_head=head,
        lab_repo=REPO, lab_pr=PR, model=MODEL, max_repairs=2,
        mode="dry-run-queue-only", scope="isolated-lab-only",
        intent="test-normalize-label-repair")
    data.update(replacements)
    return dict(id=cid, user={"id":owner}, author_association="OWNER",
        created_at="2026-10-30T01:00:00Z", updated_at="2026-10-30T01:00:00Z",
        body=HEADER+"\n"+json.dumps(data, ensure_ascii=False))


def status(comments, head=HEAD):
    ans = choose_owner_approved(comments, head)
    assert ans["execution_authority_granted"] is False
    assert ans["model_started"] is False
    assert ans["ledger_claimed"] is False
    return ans["status"]


class ReadOnlySelection(unittest.TestCase):
    def test_new_valid_owner_candidate_requires_signed_admission(self):
        result=choose_owner_approved([ticket()], HEAD)
        self.assertEqual(result["status"],"CANDIDATE_REQUIRES_INDEPENDENT_LEDGER_ADMISSION")
        self.assertEqual(result["candidate_comment_id"],17)
        self.assertFalse(result["execution_authority_granted"])
    def test_new_old_sha_is_not_reused(self):
        self.assertEqual(status([ticket(PAST)]),"WAIT_NEW_OWNER_APPROVED_CURRENT_HEAD_MISSION")
    def test_new_other_comment_is_not_work(self):
        self.assertEqual(status([{"body":"please do arbitrary code"}]),"WAIT_NEW_OWNER_APPROVED_CURRENT_HEAD_MISSION")
    def test_new_empty_queue_waits(self):
        self.assertEqual(status([]),"WAIT_NEW_OWNER_APPROVED_CURRENT_HEAD_MISSION")
    def test_new_wrong_owner_halts(self):
        self.assertEqual(status([ticket(owner=999)]),"STOP_INVALID_OWNER_MISSION")
    def test_new_wrong_task_halts(self):
        self.assertEqual(status([ticket(task_id="OTHER-TASK")]),"STOP_INVALID_OWNER_MISSION")
    def test_new_wrong_model_halts(self):
        self.assertEqual(status([ticket(model="metered")]),"STOP_INVALID_OWNER_MISSION")
    def test_new_malformed_old_mission_does_not_hide(self):
        self.assertEqual(status([ticket(PAST, owner=999)]),"STOP_INVALID_OWNER_MISSION")
    def test_new_edited_comment_halts(self):
        c=ticket();c["updated_at"]="2026-10-30T02:00:00Z"
        self.assertEqual(status([c]),"STOP_INVALID_OWNER_MISSION")
    def test_new_bad_pr_sha_halts(self):
        self.assertEqual(status([ticket()], head="x"*40),"STOP_INVALID_REMOTE_HEAD")
    def test_new_duplicate_id_halts(self):
        self.assertEqual(status([ticket(),ticket()]),"STOP_DUPLICATE_OR_UNAPPROVED_MISSION")
    def test_new_oldest_first_is_deterministic_not_dispatch(self):
        result=choose_owner_approved([ticket(cid=18),ticket(cid=17)],HEAD)
        self.assertEqual(result["candidate_comment_id"],17)
        self.assertFalse(result["execution_authority_granted"])
    def test_new_full_page_fails_closed(self):
        self.assertEqual(status([{"body":"ordinary"}]*100),
                         "STOP_INCOMPLETE_OR_UNTRUSTED_COMMENT_PAGE")
    def test_new_untrusted_item_fails_closed(self):
        self.assertEqual(status([None]),"STOP_UNTRUSTED_COMMENT")

    def test_new_readback_real_pr_contract_with_mocked_http(self):
        data=[
            dict(number=PR,state="open",draft=True,head=dict(ref=BRANCH,sha=HEAD,
                repo=dict(full_name=REPO)),base=dict(repo=dict(full_name=REPO))),
            [ticket()]
        ]
        class Response:
            status=200
            def __init__(self,url,obj):self.url=url;self.obj=obj
            def __enter__(self):return self
            def __exit__(self,*args):return None
            def geturl(self):return self.url
            def read(self,n):return json.dumps(self.obj).encode()
        def get(request,timeout):
            return Response(request.full_url,data.pop(0))
        result=read_only_live_discovery(opener=get)
        self.assertEqual(result["status"],"CANDIDATE_REQUIRES_INDEPENDENT_LEDGER_ADMISSION")
        self.assertEqual(result["candidate_comment_id"],17)
        self.assertFalse(result["execution_authority_granted"])


if __name__ == "__main__":
    unittest.main()
