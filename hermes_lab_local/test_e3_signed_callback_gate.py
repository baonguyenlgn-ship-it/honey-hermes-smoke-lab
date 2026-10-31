"""New E3 signed callback contract adversarial tests; ephemeral test key ONLY.

No private host key, no Codespace call, no model, no callback, no external
writes. Tests must never be labelled 'live callback delivered'.
"""
import base64
import copy
import hashlib
import unittest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from hermes_lab_local.e3_signed_callback_gate import (
    AUDIENCE, TASK, CallbackDenied, canonical, verify_signed_callback_eligibility,
)
from hermes_lab_local.e3_owner_comment_admission import (
    AUDIENCE as OWNER_AUD, EXPECTED_HEAD, PR_NUMBER, REPO,
)

NOW=1800000000
RUN=2468024
CID=654320111
JTI="test-only-e3-no-custody-00001"
PERMIT="a"*64
SOURCE="b"*64
HOST="test-codespace-not-real"
ISSUER="ephemeral-fixture-not-real"
WORKER="uid:999:honey-hermes-test"

def fixtures():
    key=Ed25519PrivateKey.generate()
    public=key.public_key().public_bytes(
        serialization.Encoding.Raw,serialization.PublicFormat.Raw)
    callback_id="cb-"+hashlib.sha256(
        (REPO+"|"+JTI+"|"+str(RUN)).encode()).hexdigest()
    payload={
        "aud":AUDIENCE,"repo":REPO,"pr":PR_NUMBER,"pr_head":EXPECTED_HEAD,
        "owner_comment_id":CID,"task_id":TASK,"lease_jti":JTI,
        "runtime_permit_sha256":PERMIT,"host_id":HOST,"issuer_id":ISSUER,
        "worker_actor":WORKER,"worker_run_id":RUN,
        "worker_source_sha256":SOURCE,"worker_qa_status":"INDEPENDENT_QA_PASS",
        "callback_id":callback_id,"issued_at":NOW-2,"expires_at":NOW+80,
        "production_authorized":False,"paid_provider_allowed":False,
    }
    owner={
        "aud":OWNER_AUD,"status":"AUTHENTICATED_OWNER_READONLY_INTENT_NOT_EXECUTED",
        "repo":REPO,"pr":PR_NUMBER,"pr_head":EXPECTED_HEAD,
        "comment_id":CID,"execution_authorized":False,"runtime_permit_issued":False,
    }
    run={
        "id":RUN,"repository":{"full_name":REPO},
        "head_sha":EXPECTED_HEAD,"status":"completed","conclusion":"success",
    }
    ledger={
        "jti":JTI,"owner_comment_id":CID,"runtime_permit_sha256":PERMIT,
        "worker_run_id":RUN,"worker_source_sha256":SOURCE,
        "status":"CLAIMED_COMPLETED_QA_PASS","callback_consumed":False,
    }
    return key,public,payload,owner,run,ledger

def signed(key,claims):
    return {"claims":copy.deepcopy(claims),
            "sig_b64":base64.b64encode(key.sign(canonical(claims))).decode()}

class E3CallbackBoundary(unittest.TestCase):
    def run_case(self,*,mutate_claims=None,mutate_owner=None,
                 mutate_run=None,mutate_ledger=None,at=NOW,
                 wrong_key=False,expected_error=None):
        key,pub,payload,owner,run,ledger=fixtures()
        if mutate_claims:mutate_claims(payload)
        if mutate_owner:mutate_owner(owner)
        if mutate_run:mutate_run(run)
        if mutate_ledger:mutate_ledger(ledger)
        if wrong_key:
            key=Ed25519PrivateKey.generate()
        x=signed(key,payload)
        fn=lambda:verify_signed_callback_eligibility(
            x,enrolled_public_key=pub,
            independently_verified_owner_intent=owner,
            verified_worker_run=run,verified_ledger=ledger,
            expected_host_id=HOST,expected_issuer_id=ISSUER,
            expected_worker_actor=WORKER,now=at)
        if expected_error:
            with self.assertRaisesRegex(CallbackDenied,expected_error):fn()
        else:
            r=fn()
            self.assertEqual(r["status"],"E3_SIGNED_CALLBACK_ELIGIBLE_NOT_DELIVERED")
            self.assertFalse(r["callback_delivered"])
            self.assertFalse(r["ledger_write_performed"])
            self.assertFalse(r["auto_next_dispatched"])
    def test_exact_source_contract_only_succeeds_as_not_delivered(self):self.run_case()
    def test_unknown_signer_denied(self):self.run_case(wrong_key=True,expected_error="SIGNATURE")
    def test_rebound_head_denied(self):self.run_case(
        mutate_claims=lambda c:c.update(pr_head="c"*40),expected_error="SCOPE")
    def test_rebound_owner_denied(self):self.run_case(
        mutate_claims=lambda c:c.update(owner_comment_id=CID+1),expected_error="SCOPE")
    def test_old_jti_denied(self):self.run_case(
        mutate_claims=lambda c:c.update(lease_jti="another-jti-not-from-host"),
        expected_error="SCOPE")
    def test_invalid_permit_digest_denied(self):self.run_case(
        mutate_claims=lambda c:c.update(runtime_permit_sha256="not-a-hash"),
        expected_error="SCOPE")
    def test_wrong_worker_id_denied(self):self.run_case(
        mutate_claims=lambda c:c.update(worker_actor="uid:0:root"),expected_error="SCOPE")
    def test_wrong_task_denied(self):self.run_case(
        mutate_claims=lambda c:c.update(task_id="unapproved-paid-task"),expected_error="SCOPE")
    def test_prod_flag_denied(self):self.run_case(
        mutate_claims=lambda c:c.update(production_authorized=True),expected_error="SCOPE")
    def test_paid_flag_denied(self):self.run_case(
        mutate_claims=lambda c:c.update(paid_provider_allowed=True),expected_error="SCOPE")
    def test_expired_denied(self):self.run_case(at=NOW+81,expected_error="NOT_FRESH")
    def test_boolean_time_denied(self):self.run_case(
        mutate_claims=lambda c:c.update(issued_at=True),expected_error="NOT_FRESH")
    def test_more_than_five_minutes_denied(self):self.run_case(
        mutate_claims=lambda c:c.update(expires_at=NOW+400),expected_error="NOT_FRESH")
    def test_wrong_cas_callback_id_denied(self):self.run_case(
        mutate_claims=lambda c:c.update(callback_id="cb-altered"),expected_error="SCOPE")
    def test_owner_authority_escalation_denied(self):self.run_case(
        mutate_owner=lambda o:o.update(execution_authorized=True),expected_error="OWNER_INTENT")
    def test_run_no_success_denied(self):self.run_case(
        mutate_run=lambda r:r.update(conclusion="failure"),expected_error="WORKER_RUN")
    def test_run_wrong_head_denied(self):self.run_case(
        mutate_run=lambda r:r.update(head_sha="f"*40),expected_error="WORKER_RUN")
    def test_ledger_unclaimed_denied(self):self.run_case(
        mutate_ledger=lambda l:l.update(status="NOT_CLAIMED"),expected_error="LEDGER")
    def test_ledger_already_consumed_denied(self):self.run_case(
        mutate_ledger=lambda l:l.update(callback_consumed=True),expected_error="LEDGER")
    def test_ledger_different_source_denied(self):self.run_case(
        mutate_ledger=lambda l:l.update(worker_source_sha256="c"*64),expected_error="LEDGER")
    def test_bad_signature_encoding_denied(self):
        key,pub,payload,owner,run,ledger=fixtures()
        forged=signed(key,payload);forged["sig_b64"]="bad--"
        with self.assertRaises(CallbackDenied):
            verify_signed_callback_eligibility(
                forged,enrolled_public_key=pub,independently_verified_owner_intent=owner,
                verified_worker_run=run,verified_ledger=ledger,
                expected_host_id=HOST,expected_issuer_id=ISSUER,
                expected_worker_actor=WORKER,now=NOW)

if __name__=="__main__":unittest.main()
