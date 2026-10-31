"""New E1-only source/manifest contract tests. Fixture != actual model QA."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from hermes_lab_local.e1_durable_new_task import (
    ISOLATED_BRANCH, TASK_ID, PREDECESSOR_RUN, qa_new_e1_task,
)
from hermes_lab_local.e1_independent_artifact_verify import (
    ArtifactVerificationFailed, verify_original_artifact,
)
from hermes_lab_local.windows_local_hermes_coding import QaRejected, PINNED_HERMES

SOURCE = "def stock_gap(available, minimum):\n    return int(minimum) - int(available)"
SHA = "c" * 40
RUN = 99999

def fixture(folder, source=SOURCE):
    raw = source.encode("utf-8")
    (folder / "original_model_generated.py").write_bytes(raw)
    manifest = {
        "schema": "honey.hermes.real-model-durable-evidence.v1",
        "task_id": TASK_ID, "evidence_kind": "UNSIGNED_ISOLATED_LOOPBACK_TEST",
        "source_filename": "original_model_generated.py",
        "source_sha256": hashlib.sha256(raw).hexdigest(), "source_bytes": len(raw),
        "source_branch": ISOLATED_BRANCH, "source_commit": SHA,
        "github_run_id": RUN, "predecessor_windows_run": PREDECESSOR_RUN,
        "model_attempts": 1, "repairs": 0,
        "model": "local-loopback-Qwen2.5-Coder-1.5B",
        "hermes_upstream_sha": PINNED_HERMES,
        "qa": "AST_ALLOWLIST_PLUS_BEHAVIOR",
        "independent_download_qa": "PENDING",
        "signed_gate_b": False, "production_authorized": False,
        "unattended_dispatch_proven": False,
    }
    (folder / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return manifest

class NewE1SourceTests(unittest.TestCase):
    def test_functionally_equivalent_safe_stock_gap(self):
        variants = (
            SOURCE,
            "def stock_gap(available, minimum):\n    available = int(available)\n    minimum = int(minimum)\n    return minimum - available",
            "def stock_gap(available, minimum):\n    return int(minimum) + (0 - int(available))",
        )
        # The last variant may be rejected by the intentionally tight grammar.
        for src in variants[:2]:
            with self.subTest(src=src):
                self.assertEqual(qa_new_e1_task(src), src.encode())

    def test_unsafe_or_wrong_model_source_is_denied(self):
        for source in (
            "import os\n" + SOURCE,
            "def stock_gap(available, minimum):\n    return int(available)-int(minimum)",
            "def stock_gap(available, minimum):\n    return int(minimum)-int(available) + 1",
            "def stock_gap(available, minimum):\n    return __import__('os').getcwd()",
            "def stock_gap(available, minimum):\n    while True: pass",
            "def stock_gap(available, minimum):\n    return open('secret')",
            "def stock_gap(available, minimum):\n    return 0",
        ):
            with self.subTest(prefix=source[:28]):
                with self.assertRaises(QaRejected):
                    qa_new_e1_task(source)

    def test_fixture_manifest_readback_matches_bytes_and_QA(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            fixture(folder)
            x=verify_original_artifact(folder,sha=SHA,run_id=RUN)
            self.assertEqual(x["status"],"HERMES_E1_INDEPENDENT_GITHUB_WINDOWS_DOWNLOADED_ORIGINAL_QA_PASS")
            self.assertEqual(x["original_source_sha256"],hashlib.sha256(SOURCE.encode()).hexdigest())
            self.assertFalse(x["signed_gate_b"])

    def test_changed_original_bytes_denied_not_reconstructed(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            fixture(folder)
            (folder/"original_model_generated.py").write_text(SOURCE+"\n# changed")
            with self.assertRaisesRegex(ArtifactVerificationFailed,"SHA256_MISMATCH"):
                verify_original_artifact(folder,sha=SHA,run_id=RUN)

    def test_wrong_run_or_commit_denied(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            fixture(folder)
            for source_sha, run in ((SHA,RUN+1), ("d"*40,RUN)):
                with self.subTest(run=run, source_sha=source_sha):
                    with self.assertRaises(ArtifactVerificationFailed):
                        verify_original_artifact(folder,sha=source_sha,run_id=run)

    def test_extra_files_are_denied(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            fixture(folder)
            (folder/"secret").write_text("x")
            with self.assertRaisesRegex(ArtifactVerificationFailed,"FILES_UNEXPECTED"):
                verify_original_artifact(folder,sha=SHA,run_id=RUN)

    def test_writable_scope_flags_not_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            d=fixture(folder)
            d["production_authorized"]=True
            (folder/"manifest.json").write_text(json.dumps(d))
            with self.assertRaisesRegex(ArtifactVerificationFailed,"SCOPE_NOT_MATCHED"):
                verify_original_artifact(folder,sha=SHA,run_id=RUN)

    def test_valid_hash_with_semantically_wrong_model_source_is_rejected(self):
        bad="def stock_gap(available, minimum):\n    return int(available) - int(minimum)"
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            fixture(folder,bad)
            with self.assertRaisesRegex(ArtifactVerificationFailed,"DOWNLOADED_CODE_FAILED"):
                verify_original_artifact(folder,sha=SHA,run_id=RUN)

if __name__=="__main__":
    unittest.main()
