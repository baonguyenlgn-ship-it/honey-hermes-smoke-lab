"""Only NEW bounded next-step planning tests; no network, model, or secrets."""
import unittest
from hermes_lab_local.automatic_next_step import next_safe_step, TASK, MODEL, BRANCH


def base(**updates):
    s = dict(task_id=TASK, model=MODEL, branch=BRANCH,
        head="a" * 40, verified_head="a" * 40,
        lease_current=True, live_consent_bound=True, ledger_claimed=True,
        attempt_started=True, provider_ack_verified=True, provider_error=False,
        uncertain_effect=False, qa_status="PASS", qa_ref="job:qa-123",
        repairs=0, published=True, windows_verified=True,
        callback_verified=True, independent_evidence=True)
    s.update(updates)
    return s


class NewNextStepTests(unittest.TestCase):
    def check(self, expected, **changes):
        got=next_safe_step(base(**changes))
        self.assertEqual(got["next_safe_step"], expected)
        self.assertFalse(got["execution_authority_granted"])
        self.assertFalse(got["production_authorized"])

    def test_done_await_new_approved_mission(self): self.check("WAIT_NEXT_EXPLICITLY_APPROVED_MISSION")
    def test_new_missing_inputs_denied(self): self.assertEqual(next_safe_step({})["next_safe_step"], "STOP_UNTRUSTED_OR_INCOMPLETE_STATE")
    def test_new_extra_inputs_denied(self): self.check("STOP_UNTRUSTED_OR_INCOMPLETE_STATE", root=True)
    def test_new_bad_task_denied(self): self.check("STOP_STALE_HEAD_OR_UNAPPROVED_TASK", task_id="unscoped")
    def test_new_wrong_model_denied(self): self.check("STOP_STALE_HEAD_OR_UNAPPROVED_TASK", model="upstage/solar-mini4")
    def test_new_wrong_branch_denied(self): self.check("STOP_STALE_HEAD_OR_UNAPPROVED_TASK", branch="main")
    def test_new_sha_drift_denied(self): self.check("STOP_STALE_HEAD_OR_UNAPPROVED_TASK", verified_head="b"*40)
    def test_new_negative_repairs_denied(self): self.check("STOP_INVALID_QA_HISTORY", repairs=-1)
    def test_new_overlimit_repairs_denied(self): self.check("STOP_INVALID_QA_HISTORY", repairs=3)
    def test_new_no_independent_provenance_denied(self): self.check("STOP_INDEPENDENT_READBACK_MISSING", independent_evidence=False)
    def test_new_unknown_fence(self): self.check("STOP_UNKNOWN_RECONCILE_NEVER_BLIND_RETRY", uncertain_effect=True)
    def test_new_provider_error(self): self.check("STOP_PROVIDER_FAILURE_NO_PAID_FALLBACK", provider_error=True)
    def test_new_expired_lease(self): self.check("WAIT_HOST_CUSTODIAN_NEW_SCOPED_LEASE", lease_current=False)
    def test_new_consent_bound(self): self.check("WAIT_OWNER_CONSENT_FOR_EXACT_NEW_JTI", live_consent_bound=False)
    def test_new_not_claimed(self): self.check("HOST_CUSTODIAN_CLAIM_ONCE", ledger_claimed=False, attempt_started=False, provider_ack_verified=False, qa_status="NONE",qa_ref="")
    def test_new_unclaimed_attempt_denied(self): self.check("STOP_UNCLAIMED_EXECUTION_INCONSISTENCY", ledger_claimed=False)
    def test_new_first_attempt(self): self.check("HOST_SUPERVISED_MODEL_FIRST_ATTEMPT", attempt_started=False,provider_ack_verified=False,qa_status="NONE",qa_ref="")
    def test_new_fake_initial_qa_denied(self): self.check("STOP_FABRICATED_MODEL_HISTORY",attempt_started=False)
    def test_new_missing_ack_denied(self): self.check("STOP_MODEL_OUTCOME_UNKNOWN_NO_RETRY", provider_ack_verified=False)
    def test_new_qa_wait(self): self.check("INDEPENDENT_QA_OF_REAL_CODE",qa_status="NONE",qa_ref="")
    def test_new_reject_proof_missing(self): self.check("STOP_QA_REJECTION_PROVENANCE_MISSING",qa_status="REJECT",qa_ref="")
    def test_new_repair_genuine_first(self): self.check("HOST_BOUNDED_QA_TRIGGERED_REPAIR",qa_status="REJECT",repairs=0)
    def test_new_repair_genuine_second(self): self.check("HOST_BOUNDED_QA_TRIGGERED_REPAIR",qa_status="REJECT",repairs=1)
    def test_new_repair_exhausted(self): self.check("STOP_REPAIR_BUDGET_EXHAUSTED",qa_status="REJECT",repairs=2)
    def test_new_pass_without_evidence(self): self.check("STOP_INDEPENDENT_QA_PASS_EVIDENCE_MISSING",qa_ref="")
    def test_new_publish_step(self): self.check("HOST_BROKER_PUBLISH_CAS",published=False,windows_verified=False,callback_verified=False)
    def test_new_windows_step(self): self.check("INDEPENDENT_WINDOWS_READBACK",windows_verified=False,callback_verified=False)
    def test_new_callback_step(self): self.check("VERIFY_DURABLE_OWNER_CALLBACK",callback_verified=False)
    def test_new_boolean_type_denied(self): self.check("STOP_UNTRUSTED_OR_INCOMPLETE_STATE",lease_current=1)
    def test_new_qa_undocumented_status_denied(self): self.check("STOP_INVALID_QA_HISTORY",qa_status="CLAIMED_PASS")


if __name__ == "__main__": unittest.main()
