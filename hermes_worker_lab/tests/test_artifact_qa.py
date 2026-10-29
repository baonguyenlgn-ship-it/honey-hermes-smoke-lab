"""Focused tests for byte integrity, scope, and existing admission reuse."""
from dataclasses import replace
import hashlib, tempfile, unittest
from pathlib import Path
from hermes_worker_lab import artifact_qa as qa
from hermes_worker_lab.tests import test_worker_admission as fx
from hermes_worker_lab.worker_admission import AdmissionDenied, DurableReplayLedger, WorkerAdmissionAdapter

DATA=fx.ARTIFACT_BYTES
BRANCH=fx.BRANCH

def manifest(**changes):
    v={"task_id":fx.TASK,"source_session_id":fx.SESSION_ID,"source_path":qa.SOURCE_PATH,
       "target_path":qa.ARTIFACT_PATH,"repository":qa.REPOSITORY,"workstream":fx.WORKSTREAM,
       "environment":"TEST","branch":BRANCH,"base_sha":fx.BASE,"source_sha":fx.SOURCE,
       "paths":[qa.ARTIFACT_PATH],"subject":"worker:synthetic","role":"dev-test-coder",
       "action":"code","size_bytes":len(DATA),"sha256":hashlib.sha256(DATA).hexdigest(),
       "producer_subject":"worker:synthetic","hermes_version":qa.HERMES_VERSION,
       "hermes_commit":qa.HERMES_COMMIT}
    v.update(changes); return v

def request_and_verifier():
    req=replace(fx.request(artifact_target_path=qa.ARTIFACT_PATH,paths=(qa.ARTIFACT_PATH,)),
       repository=qa.REPOSITORY)
    verifier=fx.evidence()
    verifier.values[("assignment",b"fake-assignment")]=replace(
       verifier.verify_assignment(b"fake-assignment"),repository=qa.REPOSITORY,paths=(qa.ARTIFACT_PATH,))
    verifier.values[("lease",b"fake-lease")]=replace(
       verifier.verify_lease(b"fake-lease"),repository=qa.REPOSITORY,paths=(qa.ARTIFACT_PATH,))
    verifier.values[("snapshot",b"fake-snapshot")]=replace(
       verifier.verify_guard_snapshot(b"fake-snapshot"),repository=qa.REPOSITORY)
    verifier.values[("artifact",b"fake-artifact")]=replace(
       verifier.verify_artifact(b"fake-artifact"),target_path=qa.ARTIFACT_PATH)
    return req,verifier

class ArtifactQaTests(unittest.TestCase):
    def setUp(self): self.tmp=tempfile.TemporaryDirectory()
    def tearDown(self): self.tmp.cleanup()
    def adapter(self,verifier):
        return WorkerAdmissionAdapter(repository=qa.REPOSITORY,workstream=fx.WORKSTREAM,verifier=verifier,
          replay_ledger=DurableReplayLedger(str(Path(self.tmp.name)/"ledger.sqlite")),
          expected_hermes_version=qa.HERMES_VERSION,expected_hermes_commit=qa.HERMES_COMMIT,
          expected_publisher_subject=fx.BROKER_SUBJECT)
    def test_fixture_exact_bytes_and_session_pass_as_unverified_structure(self):
        r=qa.validate_manifest_bytes(manifest(),DATA,expected_branch=BRANCH,expected_source_sha=fx.SOURCE)
        self.assertEqual((r.size_bytes,r.sha256),(len(DATA),fx.ARTIFACT))
        self.assertEqual(r.status,"BYTES_MANIFEST_SYNTAX_PASS_PROVENANCE_UNVERIFIED")
    def test_admission_wrapper_reuses_synthetic_contract_and_ledger(self):
        req,v=request_and_verifier()
        r,d=qa.validate_authenticated_artifact(manifest(),DATA,adapter=self.adapter(v),request=req,
          expected_branch=BRANCH,expected_source_sha=fx.SOURCE,now=fx.NOW)
        self.assertEqual(r.sha256,fx.ARTIFACT); self.assertEqual(d.code,"SCOPE_CONTRACT_VALID_SYNTHETIC_TESTS_ONLY")
        self.assertFalse(d.side_effects_performed)
        replay_result,replay=qa.validate_authenticated_artifact(manifest(),DATA,adapter=self.adapter(v),request=req,
          expected_branch=BRANCH,expected_source_sha=fx.SOURCE,now=fx.NOW)
        self.assertTrue(replay.replay)
    def test_missing_and_mutated_bytes_fail_closed(self):
        with self.assertRaisesRegex(qa.ArtifactQaError,"ORIGINAL_BYTES_MISSING"):
            qa.validate_manifest_bytes(manifest(),None,expected_branch=BRANCH)
        changed=DATA[:-1]+bytes([DATA[-1]^1])
        with self.assertRaisesRegex(qa.ArtifactQaError,"ARTIFACT_SIZE_MISMATCH"):
            qa.validate_manifest_bytes(manifest(),DATA+b"x",expected_branch=BRANCH)
        with self.assertRaisesRegex(qa.ArtifactQaError,"ARTIFACT_SHA_MISMATCH"):
            qa.validate_manifest_bytes(manifest(size_bytes=len(changed)),changed,expected_branch=BRANCH)
    def test_wrong_size_sha_task_source_path_or_branch_denied(self):
        cases=[
          (manifest(size_bytes=len(DATA)+1),{},"ARTIFACT_SIZE_MISMATCH"),
          (manifest(sha256="0"*64),{},"ARTIFACT_SHA_MISMATCH"),
          (manifest(task_id="OTHER-TASK-0001"),{"expected_task_id":fx.TASK},"TASK_ID_MISMATCH"),
          (manifest(source_sha="c"*40),{"expected_source_sha":fx.SOURCE},"SOURCE_PIN_MISMATCH"),
          (manifest(target_path="../escape.py"),{},"TARGET_PATH_INVALID"),
          (manifest(source_path="/tmp/forged.py"),{},"SOURCE_PATH_MISMATCH"),
          (manifest(branch="main"),{},"BRANCH_OR_ENVIRONMENT_SCOPE_MISMATCH"),
        ]
        for m,k,code in cases:
            with self.subTest(code=code),self.assertRaisesRegex(qa.ArtifactQaError,code):
                qa.validate_manifest_bytes(m,DATA,expected_branch=BRANCH,**k)
    def test_wrong_session_and_payload_binding_denied_by_authenticated_gate(self):
        req,v=request_and_verifier()
        with self.assertRaisesRegex(qa.ArtifactQaError,"ADMISSION_MANIFEST_BINDING_MISMATCH"):
            qa.validate_authenticated_artifact(manifest(source_session_id="FOREIGN"),DATA,
              adapter=self.adapter(v),request=req,expected_branch=BRANCH,expected_source_sha=fx.SOURCE,now=fx.NOW)
        changed=DATA+b"x"
        changed_manifest=manifest(size_bytes=len(changed),sha256=hashlib.sha256(changed).hexdigest())
        with self.assertRaisesRegex(qa.ArtifactQaError,"ADMISSION_BYTES_MISMATCH"):
            qa.validate_authenticated_artifact(changed_manifest,changed,adapter=self.adapter(v),
              request=req,expected_branch=BRANCH,expected_source_sha=fx.SOURCE,now=fx.NOW)
    def test_forged_producer_receipt_denied_by_existing_verifier(self):
        req,v=request_and_verifier()
        original=v.verify_artifact(b"fake-artifact")
        v.values[("artifact",b"fake-artifact")]=replace(original,producer_subject="worker:forged")
        with self.assertRaisesRegex(AdmissionDenied,"ARTIFACT_PROVENANCE_MISMATCH"):
            qa.validate_authenticated_artifact(manifest(),DATA,adapter=self.adapter(v),request=req,
              expected_branch=BRANCH,expected_source_sha=fx.SOURCE,now=fx.NOW)
    def test_single_backslash_in_path_is_denied(self):
        unsafe=r"hermes_worker_lab\artifacts\forged.py"
        with self.assertRaisesRegex(qa.ArtifactQaError,"PATH_SET_INVALID"):
            qa.validate_manifest_bytes(manifest(paths=[qa.ARTIFACT_PATH,unsafe]),DATA,expected_branch=BRANCH)

    def test_wrong_repo_hermes_pin_and_manifest_shape_denied(self):
        for m,code in [(manifest(repository="other/repo"),"REPOSITORY_SCOPE_MISMATCH"),
           (manifest(hermes_version="0.22.4"),"HERMES_VERSION_MISMATCH"),
           (manifest(hermes_commit="f"*40),"HERMES_COMMIT_MISMATCH"),
           ({**manifest(),"extra":"forged"},"MANIFEST_FIELDS_INVALID")]:
            with self.subTest(code=code),self.assertRaisesRegex(qa.ArtifactQaError,code):
                qa.validate_manifest_bytes(m,DATA,expected_branch=BRANCH)
    def test_symlink_or_missing_artifact_reports_waiting_or_denies(self):
        root=Path(self.tmp.name); result=qa.check_checkout(root,expected_branch=BRANCH) if False else None
        with self.assertRaisesRegex(qa.ArtifactQaError,"WAITING_ORIGINAL_BYTES"):
            qa.check_checkout(root,expected_branch=BRANCH)
        artifact=root/qa.ARTIFACT_PATH; artifact.parent.mkdir(parents=True)
        artifact.symlink_to(Path(self.tmp.name)/"outside")
        (root/qa.MANIFEST_PATH).write_text("{}")
        with self.assertRaises((qa.ArtifactQaError,OSError)):
            qa.check_checkout(root,expected_branch=BRANCH)

if __name__=="__main__": unittest.main()
