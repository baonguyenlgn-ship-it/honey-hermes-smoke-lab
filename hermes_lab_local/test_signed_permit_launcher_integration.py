"""Only NEW Gate-B signed-permit→ledger→worker ordering checks.

Uses the real Ed25519 verifier with a fresh ephemeral unit-test key, while
ALL host I/O, mission/consent readback, claim and model/broker subprocess
calls are mocked. This MUST NOT be reported as Hermes AI E2E.
"""
import os
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from hermes_lab_local.live_execution_gate import (
    AdmissionDenied, run_supervised_once, LEASE_FILE, PERMIT_FILE,
    FREE_EVIDENCE, HOST, REPAIR_SCRIPT, BROKER_COMMAND
)
from hermes_lab_local.test_signed_runtime_permit import (
    fixture, sign, NOW, OWNER_COMMENT_ID
)
from hermes_lab_local.v31.one_use_lease_gate import MODEL


class NewSignedPermitLauncherContract(unittest.TestCase):
    def case(self, *, alter=None, permit_present=True, claimed=None,
             fake_rcs=(0, 0), protected_permit_changed_at=None,
             paid=False, expect=None, expected_runner_calls=None):
        key, host, bound_ticket, lease, permit_claims = fixture()
        signed_permit = sign(key, permit_claims)
        ready = dict(
            permitted_to_execute=False,
            bound_ticket=bound_ticket,
            consent=dict(status="OWNER_LIVE_INTENT_VALIDATED_NOT_EXECUTED",
                         owner_live_comment_id=OWNER_COMMENT_ID,
                         lease_jti=lease["claims"]["jti"],
                         head=lease["claims"]["head"]),
        )
        receipt = dict(
            status="CLAIMED_NOT_EXECUTED",
            owner_live_comment_id=OWNER_COMMENT_ID,
            jti=lease["claims"]["jti"],
            expected_head=lease["claims"]["head"],
            permitted_to_execute=False,
        )
        if claimed is not None:
            receipt.update(claimed)
        if alter:
            alter(ready, signed_permit, lease)
        quote = dict(
            schema="honey.hermes.host-free-account-readback.v1",
            source="AUTHENTICATED_NOUS_ACCOUNT", plan="FREE",
            model_id=MODEL, account_free_verified=True,
            input_usd_per_million=0, output_usd_per_million=0,
            observed_at=NOW-4, no_paid_fallback=True,
        )
        if paid:
            quote["input_usd_per_million"]=1
        calls={"permit":0}
        def safe_file(path):
            if path==LEASE_FILE:
                return lease
            if path==FREE_EVIDENCE:
                return quote
            if path==PERMIT_FILE:
                calls["permit"]+=1
                if not permit_present:
                    raise AdmissionDenied("HOST_EVIDENCE_UNAVAILABLE")
                if protected_permit_changed_at == calls["permit"]:
                    return {"not": "the signed permit"}
                return signed_permit
            raise AssertionError("wrong protected host source")
        responses=iter(fake_rcs)
        runner = Mock(side_effect=lambda *args,**kwargs:
                      SimpleNamespace(returncode=next(responses)))
        claim_mock=Mock(return_value=receipt)
        with patch("hermes_lab_local.live_execution_gate.os.geteuid",
                   return_value=1000,create=True), patch.dict(
                   os.environ,{"CODESPACES":"true","CODESPACE_NAME":HOST}), patch(
                   "hermes_lab_local.live_execution_gate.protected_json",
                   side_effect=safe_file), patch(
                   "hermes_lab_local.live_execution_gate.trusted_context",
                   return_value=host), patch(
                   "hermes_lab_local.live_execution_gate.fence_check",
                   return_value="fence-stable"), patch(
                   "hermes_lab_local.live_execution_gate.time.time",
                   return_value=NOW), patch(
                   "hermes_lab_local.live_execution_gate.fetch_snapshot",
                   return_value=({"number":4},{"id":6523530512})), patch(
                   "hermes_lab_local.live_execution_gate.fetch_live_consent",
                   return_value={"id":OWNER_COMMENT_ID}), patch(
                   "hermes_lab_local.live_execution_gate.prepare",
                   return_value=ready), patch(
                   "hermes_lab_local.live_execution_gate.claim",claim_mock):
            if expect:
                with self.assertRaisesRegex(AdmissionDenied,expect):
                    run_supervised_once(OWNER_COMMENT_ID,run_command=runner)
            else:
                result=run_supervised_once(OWNER_COMMENT_ID,run_command=runner)
                self.assertEqual(
                    result["status"],
                    "HOST_EXECUTED_AWAITING_INDEPENDENT_WINDOWS_QA")
                self.assertEqual(result["gate_b"],"NOT_PROVEN")
                self.assertEqual(result["jti"],lease["claims"]["jti"])
            if expected_runner_calls is not None:
                self.assertEqual(runner.call_count,expected_runner_calls)
            if expect in ("EXECUTION_PERMISSION_NOT_GRANTED",
                          "NO_VERIFIED_ZERO_COST_FREE_ACCOUNT"):
                claim_mock.assert_not_called()
            for call in runner.call_args_list:
                self.assertIn(call.args[0],(REPAIR_SCRIPT,BROKER_COMMAND))
        return runner

    def test_new_real_signature_contract_can_advance_only_with_fake_runner(self):
        r=self.case(expected_runner_calls=2)
        self.assertEqual(r.call_args_list[0].args[0],REPAIR_SCRIPT)
        self.assertEqual(r.call_args_list[1].args[0],BROKER_COMMAND)

    def test_new_no_host_permit_no_ledger_or_worker(self):
        self.case(permit_present=False,expect="EXECUTION_PERMISSION_NOT_GRANTED",
                  expected_runner_calls=0)

    def test_new_reject_tampered_permit_before_claim(self):
        self.case(alter=lambda ready,p,l:p["claims"].update(model="metered"),
                  expect="EXECUTION_PERMISSION_NOT_GRANTED",expected_runner_calls=0)

    def test_new_reject_different_lease_jti_before_claim(self):
        self.case(alter=lambda ready,p,l:ready["consent"].update(
                      lease_jti="different-not-authorized"),
                  expect="EXECUTION_PERMISSION_NOT_GRANTED",expected_runner_calls=0)

    def test_new_reject_different_owner_consent_before_claim(self):
        self.case(alter=lambda ready,p,l:ready["consent"].update(
                      owner_live_comment_id=1111),
                  expect="EXECUTION_PERMISSION_NOT_GRANTED",expected_runner_calls=0)

    def test_new_reject_current_v31_flag_escalation(self):
        self.case(alter=lambda ready,p,l:ready.update(permitted_to_execute=True),
                  expect="EXECUTION_PERMISSION_NOT_GRANTED",expected_runner_calls=0)

    def test_new_reject_broken_claim_receipt_before_model(self):
        self.case(claimed={"permitted_to_execute":True},
                  expect="CLAIM_RECEIPT_NOT_ADMISSION_ONLY_NO_RETRY",
                  expected_runner_calls=0)

    def test_new_changed_permit_after_claim_never_starts_model(self):
        self.case(protected_permit_changed_at=2,
                  expect="RUNTIME_PERMIT_CHANGED_NO_RETRY",
                  expected_runner_calls=0)

    def test_new_changed_permit_after_model_never_starts_broker(self):
        self.case(protected_permit_changed_at=3,
                  expect="RUNTIME_PERMIT_CHANGED_NO_RETRY",
                  expected_runner_calls=1)

    def test_new_paid_account_quote_blocks_before_claim(self):
        self.case(paid=True,expect="NO_VERIFIED_ZERO_COST_FREE_ACCOUNT",
                  expected_runner_calls=0)

    def test_new_failed_model_stops_no_broker_retry(self):
        self.case(fake_rcs=(7,),expect="MODEL_OR_QA_BLOCKED_NO_RETRY",
                  expected_runner_calls=1)

    def test_new_lease_signature_changed_wont_authorize_execution(self):
        self.case(alter=lambda ready,p,l:l["claims"].update(
                      head="d"*40),expect="EXECUTION_PERMISSION_NOT_GRANTED",
                  expected_runner_calls=0)


if __name__=="__main__":
    unittest.main()
