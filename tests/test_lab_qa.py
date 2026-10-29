"""Independent PR #2 QA and fake-data artifact-manifest verifier."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest


_HERE = Path(__file__).resolve().parent
SOURCE = _HERE / "lab_task_runner.py"
if not SOURCE.is_file():
    SOURCE = _HERE.parent / "lab_task_runner.py"
SPEC = importlib.util.spec_from_file_location("pr2_runner", SOURCE)
RUNNER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUNNER)


class ManifestError(ValueError):
    pass


def verify_manifest(manifest, artifact, expected_source_sha, seen):
    required = {"task_id", "size", "sha256", "source_sha"}
    if not isinstance(manifest, dict) or set(manifest) != required:
        raise ManifestError("manifest_shape")
    task_id = manifest["task_id"]
    size = manifest["size"]
    sha = manifest["sha256"]
    source_sha = manifest["source_sha"]
    if not isinstance(task_id, str) or not task_id:
        raise ManifestError("task_id")
    if isinstance(size, bool) or not isinstance(size, int) or size < 0:
        raise ManifestError("size")
    for name, value in (("sha256", sha), ("source_sha", source_sha)):
        if not isinstance(value, str) or len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value):
            raise ManifestError(name)
    if source_sha != expected_source_sha:
        raise ManifestError("source_mismatch")
    actual_sha = hashlib.sha256(artifact).hexdigest()
    if size != len(artifact):
        raise ManifestError("size_mismatch")
    if sha != actual_sha:
        raise ManifestError("sha256_mismatch")
    identity = (size, sha, source_sha)
    previous = seen.get(task_id)
    if previous is not None:
        if previous == identity:
            return "duplicate"
        raise ManifestError("task_mismatch")
    seen[task_id] = identity
    return "verified"


class RunnerQATests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.db = self.root / "ledger.db"

    def tearDown(self):
        self.tmp.cleanup()

    def cli(self, payload, *args, db=None):
        return subprocess.run(
            [sys.executable, str(SOURCE), "--db", str(db or self.db), *args],
            input=payload,
            text=True,
            capture_output=True,
            timeout=20,
        )

    def assert_error(self, result, exit_code, error_code):
        self.assertEqual(result.returncode, exit_code, result.stderr)
        parsed = json.loads(result.stdout)
        self.assertEqual(parsed["status"], "error")
        self.assertEqual(parsed["error"]["code"], error_code)
        return parsed

    def test_malformed_json_is_json_error(self):
        self.assert_error(self.cli('{"task_id":'), 1, "invalid_json")

    def test_empty_input_is_json_error(self):
        self.assert_error(self.cli(""), 1, "invalid_json")

    def test_non_object_json_is_rejected(self):
        self.assert_error(self.cli("[]"), 1, "invalid_payload")

    def test_payload_validation_rejects_bad_types_and_keys(self):
        cases = [
            ({"task_id": "x", "text": "a", "max_length": True}, "bool"),
            ({"task_id": "x", "text": 5, "max_length": 1}, "text"),
            ({"task_id": "", "text": "a", "max_length": 1}, "task_id"),
            ({"task_id": "x", "text": "a", "max_length": 0}, "positive"),
            ({"task_id": "x", "text": "a", "max_length": 1.5}, "int"),
            ({"task_id": "x", "text": "a", "max_length": 1, "extra": 1}, "unexpected"),
        ]
        for obj, message in cases:
            with self.subTest(obj=obj):
                result = self.cli(json.dumps(obj))
                parsed = self.assert_error(result, 1, "invalid_payload")
                self.assertIn(message, parsed["error"]["message"])

    def test_unicode_round_trip_and_normalization(self):
        payload = {"task_id": "kr-한글-🙂", "text": "  안녕   세계 🙂\n맛있어요  ", "max_length": 40}
        result = self.cli(json.dumps(payload, ensure_ascii=False))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {
            "task_id": payload["task_id"], "status": "completed", "output": "안녕 세계 🙂 맛있어요"
        })

    def test_duplicate_replay_and_changed_payload_rejection(self):
        first = {"task_id": "dup-1", "text": "hello world", "max_length": 5}
        a = self.cli(json.dumps(first))
        b = self.cli(json.dumps(first))
        changed = dict(first, text="changed")
        c = self.cli(json.dumps(changed))
        self.assertEqual(json.loads(a.stdout)["status"], "completed")
        self.assertEqual(json.loads(b.stdout), {"task_id": "dup-1", "status": "duplicate", "output": "hello"})
        self.assert_error(c, 3, "payload_mismatch")
        with sqlite3.connect(self.db) as conn:
            self.assertEqual(conn.execute("select output from task_ledger where task_id='dup-1'").fetchone()[0], "hello")
            self.assertEqual(conn.execute("select count(*) from task_ledger").fetchone()[0], 1)

    def test_concurrent_same_task_commits_once(self):
        payload = json.dumps({"task_id": "race-1", "text": "parallel", "max_length": 20})
        processes = [subprocess.Popen(
            [sys.executable, str(SOURCE), "--db", str(self.db)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        ) for _ in range(12)]
        results = []
        for proc in processes:
            out, err = proc.communicate(payload, timeout=30)
            self.assertEqual(proc.returncode, 0, err)
            results.append(json.loads(out))
        statuses = [item["status"] for item in results]
        self.assertEqual(statuses.count("completed"), 1)
        self.assertEqual(statuses.count("duplicate"), 11)
        with sqlite3.connect(self.db) as conn:
            self.assertEqual(conn.execute("select count(*) from task_ledger").fetchone()[0], 1)
            self.assertEqual(conn.execute("pragma integrity_check").fetchone()[0], "ok")

    def test_crash_before_commit_rolls_back_then_restart_recovers(self):
        code = (
            "import os,lab_task_runner as m; "
            "m._commit=lambda conn: os._exit(97); "
            f"m.run_task({str(self.db)!r},'crash-1','restart me',30)"
        )
        crashed = subprocess.run([sys.executable, "-c", code], cwd=str(SOURCE.parent), timeout=10)
        self.assertEqual(crashed.returncode, 97)
        with sqlite3.connect(self.db) as conn:
            self.assertEqual(conn.execute("pragma integrity_check").fetchone()[0], "ok")
            tables = conn.execute("select name from sqlite_master where type='table' and name='task_ledger'").fetchall()
            if tables:
                self.assertEqual(conn.execute("select count(*) from task_ledger").fetchone()[0], 0)
        payload = json.dumps({"task_id": "crash-1", "text": "restart me", "max_length": 30})
        recovered = self.cli(payload)
        replay = self.cli(payload)
        self.assertEqual(json.loads(recovered.stdout)["status"], "completed")
        self.assertEqual(json.loads(replay.stdout)["status"], "duplicate")

    def test_unavailable_database_path_emits_error_json(self):
        db = self.root / "missing" / "ledger.db"
        result = self.cli(json.dumps({"task_id": "write-open", "text": "x", "max_length": 1}), db=db)
        self.assert_error(result, 4, "internal_error")

    def test_commit_write_failure_rolls_back_and_emits_json(self):
        payload = json.dumps({"task_id": "commit-fail", "text": "x", "max_length": 1})
        code = (
            "import io,json,sqlite3,sys,lab_task_runner as m; "
            "m._commit=lambda conn: (_ for _ in ()).throw(sqlite3.OperationalError('injected disk write failure')); "
            f"sys.stdin=io.StringIO({payload!r}); sys.exit(m.main(['--db',{str(self.db)!r}]))"
        )
        result = subprocess.run([sys.executable, "-c", code], cwd=str(SOURCE.parent), text=True,
                                 capture_output=True, timeout=10)
        self.assert_error(result, 4, "internal_error")
        with sqlite3.connect(self.db) as conn:
            self.assertEqual(conn.execute("pragma integrity_check").fetchone()[0], "ok")
            tables = conn.execute("select name from sqlite_master where type='table' and name='task_ledger'").fetchall()
            if tables:
                self.assertEqual(conn.execute("select count(*) from task_ledger").fetchone()[0], 0)

    def test_missing_cli_argument_emits_usage_json(self):
        result = subprocess.run([sys.executable, str(SOURCE)], input="{}", text=True,
                                capture_output=True, timeout=10)
        self.assert_error(result, 2, "usage_error")


class ManifestVerifierTests(unittest.TestCase):
    def setUp(self):
        self.data = b"fake artifact bytes for manifest verifier\x00\xff"
        self.source_sha = hashlib.sha256(b"fake source fixture").hexdigest()
        self.manifest = {
            "task_id": "fake-task-001", "size": len(self.data),
            "sha256": hashlib.sha256(self.data).hexdigest(), "source_sha": self.source_sha,
        }
        self.seen = {}

    def test_fake_manifest_validates_exact_bytes(self):
        self.assertEqual(verify_manifest(self.manifest, self.data, self.source_sha, self.seen), "verified")

    def test_rejects_size_mismatch(self):
        bad = dict(self.manifest, size=len(self.data) + 1)
        with self.assertRaisesRegex(ManifestError, "size_mismatch"):
            verify_manifest(bad, self.data, self.source_sha, self.seen)

    def test_rejects_artifact_sha_mismatch(self):
        bad = dict(self.manifest, sha256="0" * 64)
        with self.assertRaisesRegex(ManifestError, "sha256_mismatch"):
            verify_manifest(bad, self.data, self.source_sha, self.seen)

    def test_rejects_source_sha_mismatch(self):
        bad = dict(self.manifest, source_sha="1" * 64)
        with self.assertRaisesRegex(ManifestError, "source_mismatch"):
            verify_manifest(bad, self.data, self.source_sha, self.seen)

    def test_deduplicates_exact_task_manifest(self):
        self.assertEqual(verify_manifest(self.manifest, self.data, self.source_sha, self.seen), "verified")
        self.assertEqual(verify_manifest(self.manifest, self.data, self.source_sha, self.seen), "duplicate")

    def test_rejects_reused_task_id_with_different_artifact(self):
        self.assertEqual(verify_manifest(self.manifest, self.data, self.source_sha, self.seen), "verified")
        other = b"different fake bytes"
        changed = dict(self.manifest, size=len(other), sha256=hashlib.sha256(other).hexdigest())
        with self.assertRaisesRegex(ManifestError, "task_mismatch"):
            verify_manifest(changed, other, self.source_sha, self.seen)

    def test_rejects_invalid_manifest_shape(self):
        with self.assertRaisesRegex(ManifestError, "manifest_shape"):
            verify_manifest({"task_id": "x"}, self.data, self.source_sha, self.seen)

    def test_false_pass_probe_detects_broken_normalizer(self):
        source = SOURCE.read_text(encoding="utf-8")
        original = 'return " ".join(text.split())[:max_length].rstrip(" ")'
        self.assertIn(original, source)
        mutant = source.replace(original, "return text", 1)
        namespace = {"__name__": "mutant_runner"}
        exec(compile(mutant, "mutant_runner.py", "exec"), namespace)
        def expected_contract(module):
            assert module["_normalize"]("a   b", 20) == "a b"
        with self.assertRaises(AssertionError):
            expected_contract(namespace)
        expected_contract({"_normalize": RUNNER._normalize})


if __name__ == "__main__":
    unittest.main(verbosity=2)
