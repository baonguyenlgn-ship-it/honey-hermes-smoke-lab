"""New cryptographic permit contract QA only; ephemeral test key is NOT custody.

No model, GitHub write, private issuer, lease ledger, or external service.
"""
import base64
import copy
import hashlib
import unittest
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from hermes_lab_local.signed_runtime_permit import (
    AUDIENCE, verify_host_execution_permit,
)
from hermes_lab_local.v31.one_use_lease_gate import (
    AdmissionDenied, TrustedHostContext, AUDIENCE as LEASE_AUD,
    REPO, BRANCH, TASK, MODEL, HOST, OUTPUT_PATHS, canonical_json,
)

NOW = 1800000000
OWNER_COMMENT_ID = 9012340001


def fixture():
    # This key lives ONLY inside deterministic test scope; never publish it.
    key = Ed25519PrivateKey.generate()
    raw = key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    host = TrustedHostContext(
        custodian_id="ephemeral-unit-test-issuer",
        public_key_ed25519=raw,
        state_db=Path("/missing/test-lease-ledger"),
        worker_actor="uid:999:honey-hermes-test",
        broker_actor="uid:1000:vscode",
    )
    ticket = dict(
        comment_id=6523530512, nonce="lab-inbox-owner-demo-20261030",
        expected_head="c" * 40, task_id=TASK,
        status="LAB_TASK_RECEIVED_NOT_RUNNING",
        authorized_for_execution=False, core_guard_authorized=False,
        production_authorized=False,
    )
    lease = dict(
        aud=LEASE_AUD, issuer=host.custodian_id,
        jti="test-only-jti-external-lease-0000001", repo=REPO,
        pr=4, branch=BRANCH, head=ticket["expected_head"], host_id=HOST,
        task_id=TASK, mission_comment_id=ticket["comment_id"],
        mission_nonce=ticket["nonce"], worker_actor=host.worker_actor,
        broker_actor=host.broker_actor, model=MODEL,
        max_repairs=2, allowed_paths=list(OUTPUT_PATHS),
        issued_at=NOW-60, expires_at=NOW+600,
        cost_policy="no-new-billable-service", mode="test-lab-once",
    )
    bundle={"claims":lease,
            "sig_b64":base64.b64encode(key.sign(canonical_json(lease))).decode("ascii")}
    permit = dict(
        aud=AUDIENCE, issuer=host.custodian_id,
        repo=REPO, pr=4, branch=BRANCH, head=lease["head"],
        task_id=TASK, model=MODEL, host_id=HOST,
        worker_actor=host.worker_actor, broker_actor=host.broker_actor,
        lease_jti=lease["jti"],
        lease_sha256=hashlib.sha256(canonical_json(bundle)).hexdigest(),
        owner_live_comment_id=OWNER_COMMENT_ID,
        allowed_paths=list(OUTPUT_PATHS), max_repairs=2,
        issued_at=NOW-2, expires_at=NOW+150,
        mode="isolated-lab-execute-once",
        cost_policy="no-new-billable-service",
        may_execute_model_once=True, may_publish_test_artifact=True,
        may_access_core=False, may_merge_main=False,
        may_deploy_production=False,
    )
    return key, host, ticket, bundle, permit


def sign(key, permit):
    return {"claims": copy.deepcopy(permit),
            "sig_b64":base64.b64encode(
                key.sign(canonical_json(permit))).decode("ascii")}


class NewRuntimePermitTests(unittest.TestCase):
    def apply(self, modify=None, *, fail=None, amend_lease=None, consent_id=OWNER_COMMENT_ID):
        key, host, ticket, bundle, p = fixture()
        if modify:
            modify(p)
        signed=sign(key,p)
        if amend_lease:
            amend_lease(bundle)
        fn=lambda:verify_host_execution_permit(
            signed, bundle, ticket, consent_id, host, now=NOW)
        if fail:
            with self.assertRaises(AdmissionDenied, msg=fail):
                fn()
        else:
            res=fn()
            self.assertEqual(res["status"],"SIGNED_SEPARATE_RUNTIME_PERMIT_ELIGIBLE_NOT_CLAIMED")
            self.assertFalse(res["execution_started"])
            self.assertFalse(res["may_access_core"])
            self.assertFalse(res["may_merge_main"])
            self.assertFalse(res["may_deploy_production"])

    def test_exact_signed_separate_permission_is_eligible_not_execution(self):
        self.apply()

    def test_no_signed_runtime_permit_denied(self):
        key,host,ticket,bundle,p=fixture()
        with self.assertRaisesRegex(AdmissionDenied,"RUNTIME_PERMIT_INVALID_SHAPE"):
            verify_host_execution_permit({},bundle,ticket,OWNER_COMMENT_ID,host,now=NOW)

    def test_unpinned_signature_denied(self):
        key,host,ticket,bundle,p=fixture()
        other=Ed25519PrivateKey.generate()
        fake=sign(other,p)
        with self.assertRaisesRegex(AdmissionDenied,"RUNTIME_PERMIT_SIGNATURE_UNVERIFIED"):
            verify_host_execution_permit(fake,bundle,ticket,OWNER_COMMENT_ID,host,now=NOW)

    def test_changing_signed_model_invalidates_signature(self):
        key,host,ticket,bundle,p=fixture()
        signed=sign(key,p)
        signed["claims"]["model"]="metered/pro"
        with self.assertRaisesRegex(AdmissionDenied,"RUNTIME_PERMIT_SIGNATURE_UNVERIFIED"):
            verify_host_execution_permit(signed,bundle,ticket,OWNER_COMMENT_ID,host,now=NOW)

    def test_wrong_jti(self): self.apply(lambda p:p.update(lease_jti="unrelated-jti"), fail="jti")
    def test_wrong_head(self): self.apply(lambda p:p.update(head="d"*40), fail="head")
    def test_wrong_repo(self): self.apply(lambda p:p.update(repo="any/other"), fail="repo")
    def test_wrong_host(self): self.apply(lambda p:p.update(host_id="other"), fail="host")
    def test_wrong_model(self): self.apply(lambda p:p.update(model="paid-model"), fail="model")
    def test_wrong_issuer(self): self.apply(lambda p:p.update(issuer="other"), fail="issuer")
    def test_wrong_audience(self): self.apply(lambda p:p.update(aud="other"), fail="aud")
    def test_unauthorized_paths(self): self.apply(lambda p:p.update(allowed_paths=[".github/workflows/prod.yml"]), fail="paths")
    def test_wrong_worker(self): self.apply(lambda p:p.update(worker_actor="uid:0"), fail="worker")
    def test_unsigned_consent_comment(self): self.apply(consent_id=OWNER_COMMENT_ID+1, fail="consent")
    def test_not_approved_to_execute(self): self.apply(lambda p:p.update(may_execute_model_once=False), fail="execute")
    def test_cannot_grant_core(self): self.apply(lambda p:p.update(may_access_core=True),fail="core")
    def test_cannot_grant_main_merge(self): self.apply(lambda p:p.update(may_merge_main=True),fail="merge")
    def test_cannot_grant_prod_deploy(self): self.apply(lambda p:p.update(may_deploy_production=True),fail="prod")
    def test_no_paid_fallback(self): self.apply(lambda p:p.update(cost_policy="paid-allowed"),fail="paid")
    def test_must_have_test_broker_permission(self): self.apply(lambda p:p.update(may_publish_test_artifact=False),fail="publish")
    def test_expired(self): self.apply(lambda p:p.update(expires_at=NOW),fail="expired")
    def test_future(self): self.apply(lambda p:p.update(issued_at=NOW+1),fail="future")
    def test_window_too_long(self): self.apply(lambda p:p.update(expires_at=NOW+301),fail="long")
    def test_outside_lease_expiry(self): self.apply(lambda p:p.update(expires_at=NOW+601),fail="lease")
    def test_permit_earlier_than_lease(self): self.apply(lambda p:p.update(issued_at=NOW-61),fail="early")
    def test_boolean_expiry_denied(self): self.apply(lambda p:p.update(issued_at=True),fail="bool")
    def test_extra_fields_denied(self): self.apply(lambda p:p.update(allow_others=True),fail="extra")
    def test_changed_signed_lease_denied(self):
        self.apply(amend_lease=lambda b:b["claims"].update(jti="other-not-verified"), fail="lease")
    def test_replaced_valid_but_different_signed_lease_denied(self):
        key,host,ticket,bundle,p=fixture()
        signed=sign(key,p)
        # Same key, new real signature with different JTI: cannot reuse permit
        bundle["claims"]["jti"]="test-only-another-lease-00000002"
        bundle["sig_b64"]=base64.b64encode(key.sign(canonical_json(bundle["claims"]))).decode()
        with self.assertRaisesRegex(AdmissionDenied,"RUNTIME_PERMIT_SCOPE_MISMATCH"):
            verify_host_execution_permit(signed,bundle,ticket,OWNER_COMMENT_ID,host,now=NOW)


if __name__=="__main__":
    unittest.main()
