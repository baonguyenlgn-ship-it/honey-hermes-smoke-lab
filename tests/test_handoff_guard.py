import hashlib
import unittest
from datetime import datetime, timedelta, timezone

from handoff_guard import (
    ALLOWED_PERMISSIONS,
    REQUIRED_PERMISSIONS,
    ArtifactManifest,
    ArtifactMismatch,
    AuthorizationClaims,
    AuthorizationRejected,
    PublicationConflict,
    PublicationRecord,
    decide_publication,
    redact_secrets,
    validate_authorization,
    verify_artifact,
)


TASK = "HERMES-LAB-AUTH-HANDOFF-20261029-01"
SOURCE_SHA = "a" * 40
BASE_SHA = "b" * 40
NOW = datetime(2026, 10, 29, 13, 0, tzinfo=timezone.utc)
PAYLOAD = b'{"status":"synthetic","label":"lab"}\n'


def manifest(**changes):
    values = {
        "task_id": TASK,
        "source_session": "synthetic-session-01",
        "source_sha": SOURCE_SHA,
        "file_name": "result.json",
        "size_bytes": len(PAYLOAD),
        "sha256": hashlib.sha256(PAYLOAD).hexdigest(),
        "branch": f"hermes-lab/task-{TASK}",
        "base_sha": BASE_SHA,
    }
    values.update(changes)
    return ArtifactManifest(**values)


class ArtifactFenceTests(unittest.TestCase):
    def test_accepts_exact_synthetic_artifact(self):
        digest = verify_artifact(
            PAYLOAD,
            manifest(),
            expected_task_id=TASK,
            expected_source_sha=SOURCE_SHA,
            expected_base_sha=BASE_SHA,
        )
        self.assertEqual(digest, hashlib.sha256(PAYLOAD).hexdigest())

    def test_rejects_changed_payload_sha(self):
        with self.assertRaisesRegex(ArtifactMismatch, "SHA-256"):
            verify_artifact(
                b"X" + PAYLOAD[1:],
                manifest(),
                expected_task_id=TASK,
                expected_source_sha=SOURCE_SHA,
                expected_base_sha=BASE_SHA,
            )

    def test_rejects_wrong_size(self):
        with self.assertRaisesRegex(ArtifactMismatch, "size"):
            verify_artifact(
                PAYLOAD,
                manifest(size_bytes=len(PAYLOAD) + 1),
                expected_task_id=TASK,
                expected_source_sha=SOURCE_SHA,
                expected_base_sha=BASE_SHA,
            )

    def test_rejects_wrong_task(self):
        with self.assertRaisesRegex(ArtifactMismatch, "task id"):
            verify_artifact(
                PAYLOAD,
                manifest(),
                expected_task_id="HERMES-LAB-AUTH-HANDOFF-OTHER",
                expected_source_sha=SOURCE_SHA,
                expected_base_sha=BASE_SHA,
            )

    def test_rejects_source_sha_drift(self):
        with self.assertRaisesRegex(ArtifactMismatch, "source SHA"):
            verify_artifact(
                PAYLOAD,
                manifest(),
                expected_task_id=TASK,
                expected_source_sha="c" * 40,
                expected_base_sha=BASE_SHA,
            )

    def test_rejects_base_sha_drift(self):
        with self.assertRaisesRegex(ArtifactMismatch, "base SHA"):
            verify_artifact(
                PAYLOAD,
                manifest(),
                expected_task_id=TASK,
                expected_source_sha=SOURCE_SHA,
                expected_base_sha="c" * 40,
            )

    def test_rejects_path_traversal_filename_and_foreign_branch(self):
        for changes, expected_message in [
            ({"file_name": "../secrets.txt"}, "filename"),
            ({"branch": "main"}, "branch"),
        ]:
            with self.subTest(changes=changes):
                with self.assertRaisesRegex(ArtifactMismatch, expected_message):
                    verify_artifact(
                        PAYLOAD,
                        manifest(**changes),
                        expected_task_id=TASK,
                        expected_source_sha=SOURCE_SHA,
                        expected_base_sha=BASE_SHA,
                    )


class PublicationIdempotencyTests(unittest.TestCase):
    def test_new_task_gets_create_decision(self):
        decision = decide_publication(
            manifest(),
            artifact_sha256=hashlib.sha256(PAYLOAD).hexdigest(),
            existing_task=None,
            existing_branch_commit=None,
        )
        self.assertEqual(decision.action, "create")
        self.assertEqual(decision.branch, f"hermes-lab/task-{TASK}")

    def test_exact_replay_is_noop(self):
        decision = decide_publication(
            manifest(),
            artifact_sha256=hashlib.sha256(PAYLOAD).hexdigest(),
            existing_task=PublicationRecord(TASK, hashlib.sha256(PAYLOAD).hexdigest(), "d" * 40),
            existing_branch_commit="d" * 40,
        )
        self.assertEqual(decision.action, "already_published")

    def test_changed_replay_and_occupied_branch_fail_closed(self):
        with self.assertRaises(PublicationConflict):
            decide_publication(
                manifest(),
                artifact_sha256="e" * 64,
                existing_task=PublicationRecord(TASK, "f" * 64, "d" * 40),
                existing_branch_commit="d" * 40,
            )
        with self.assertRaisesRegex(PublicationConflict, "refusing to overwrite"):
            decide_publication(
                manifest(),
                artifact_sha256=hashlib.sha256(PAYLOAD).hexdigest(),
                existing_task=None,
                existing_branch_commit="d" * 40,
            )

    def test_task_ledger_branch_disagreement_fails_closed(self):
        with self.assertRaisesRegex(PublicationConflict, "disagree"):
            decide_publication(
                manifest(),
                artifact_sha256=hashlib.sha256(PAYLOAD).hexdigest(),
                existing_task=PublicationRecord(TASK, hashlib.sha256(PAYLOAD).hexdigest(), "d" * 40),
                existing_branch_commit="e" * 40,
            )


class AuthorizationAndRedactionTests(unittest.TestCase):
    def claims(self, **changes):
        values = {
            "repository": "baonguyenlgn-ship-it/honey-hermes-smoke-lab",
            "permissions": REQUIRED_PERMISSIONS | {"metadata:read"},
            "expires_at": NOW + timedelta(minutes=5),
            "issuer": "synthetic-broker",
        }
        values.update(changes)
        return AuthorizationClaims(**values)

    def test_accepts_exact_repo_minimum_permissions_and_short_lifetime(self):
        validate_authorization(self.claims(), now=NOW)

    def test_rejects_wrong_repo_broad_rights_and_expired_auth(self):
        for claims in [
            self.claims(repository="baonguyenlgn-ship-it/honey-gateway-core"),
            self.claims(permissions=ALLOWED_PERMISSIONS | {"administration:write"}),
            self.claims(permissions=frozenset({"contents:read", "metadata:read"})),
            self.claims(expires_at=NOW),
        ]:
            with self.subTest(claims=claims):
                with self.assertRaises(AuthorizationRejected):
                    validate_authorization(claims, now=NOW)

    def test_redacts_github_tokens_private_keys_and_known_values(self):
        token = "ghp_" + "x" * 36
        pat = "github_pat_" + "y" * 40
        pem = "-----BEGIN PRIVATE KEY-----\nnot-a-real-key\n-----END PRIVATE KEY-----"
        output = redact_secrets(f"{token} {pat} {pem} custom-secret", ["custom-secret"])
        self.assertNotIn(token, output)
        self.assertNotIn(pat, output)
        self.assertNotIn("not-a-real-key", output)
        self.assertNotIn("custom-secret", output)
        self.assertIn("REDACTED", output)


if __name__ == "__main__":
    unittest.main(verbosity=2)
