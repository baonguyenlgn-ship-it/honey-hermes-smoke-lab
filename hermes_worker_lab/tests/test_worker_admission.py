import tempfile
import unittest
import sqlite3
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import hashlib
from pathlib import Path

from hermes_worker_lab.worker_admission import (
    AdmissionDenied,
    AdmissionRequest,
    ArtifactProvenance,
    Assignment,
    DurableReplayLedger,
    GuardSnapshot,
    IdentityClaims,
    LeaseClaims,
    PublishedEffect,
    WorkerAdmissionAdapter,
)


NOW = datetime(2026, 10, 29, 12, 0, tzinfo=timezone.utc)
BASE = "a" * 40
SOURCE = "b" * 40
ARTIFACT_BYTES = b"# Hermes-generated synthetic LAB sample\nVALUE = 7\n"
ARTIFACT = hashlib.sha256(ARTIFACT_BYTES).hexdigest()
HERMES_SHA = "bf0203a794a07aac3ff764972ab9087baa4e4f4e"
SESSION_ID = "SESSION-HERMES-TEST-0001"
BROKER_SUBJECT = "github-broker:synthetic"
REPO = "example/public-lab"
WORKSTREAM = "isolated-coding-test"
BRANCH = "lab/task-HERMES-WORKER-0001"
PATHS = ("src/example.py", "tests/test_example.py")
TASK = "HERMES-WORKER-0001"


class SyntheticVerifier:
    """Maps fixed fake receipts to claims; it performs no cryptography."""

    def __init__(self, values=None):
        self.values = values or {}

    def _get(self, receipt, kind):
        return self.values.get((kind, receipt))

    def verify_assignment(self, receipt):
        return self._get(receipt, "assignment")

    def verify_identity(self, receipt):
        return self._get(receipt, "identity")

    def verify_lease(self, receipt):
        return self._get(receipt, "lease")

    def verify_guard_snapshot(self, receipt):
        return self._get(receipt, "snapshot")

    def verify_artifact(self, receipt):
        return self._get(receipt, "artifact")


class SyntheticPublicationVerifier:
    """Returns fake publication claims; this does not authenticate GitHub."""

    def __init__(self, receipt):
        self.receipt = receipt

    def verify_publication(self, encoded_receipt):
        return self.receipt if encoded_receipt == b"fake-github-receipt" else None


def evidence(*, assignment=None, identity=None, lease=None, snapshot=None):
    assignment = assignment or Assignment(
        TASK, REPO, WORKSTREAM, "TEST", BRANCH, BASE, SOURCE,
        PATHS, "worker:synthetic", "dev-test-coder",
    )
    identity = identity or IdentityClaims(
        "issuer:synthetic", "worker:synthetic", NOW - timedelta(seconds=1),
        NOW + timedelta(minutes=1),
    )
    lease = lease or LeaseClaims(
        "lease-synthetic", "issuer:synthetic", "worker:synthetic", REPO,
        WORKSTREAM, "TEST", BRANCH, BASE, PATHS, frozenset({"code", "test", "commit", "draft-pr"}),
        "dev-test-coder", NOW - timedelta(seconds=1), NOW + timedelta(minutes=4),
        "nonce-synthetic", 2, 7,
    )
    snapshot = snapshot or GuardSnapshot(
        REPO, WORKSTREAM, "TEST", BRANCH, BASE, 2, 7, 0, NOW,
    )
    artifact = ArtifactProvenance(
        TASK, SESSION_ID, "out/example.py", "src/example.py", len(ARTIFACT_BYTES),
        hashlib.sha256(ARTIFACT_BYTES).hexdigest(), "worker:synthetic", "0.22.5", HERMES_SHA,
    )
    tokens = {
        ("assignment", b"fake-assignment"): assignment,
        ("identity", b"fake-identity"): identity,
        ("lease", b"fake-lease"): lease,
        ("snapshot", b"fake-snapshot"): snapshot,
        ("artifact", b"fake-artifact"): artifact,
    }
    return SyntheticVerifier(tokens)


def request(**changes):
    values = dict(
        assignment_receipt=b"fake-assignment",
        identity_receipt=b"fake-identity",
        lease_receipt=b"fake-lease",
        guard_snapshot_receipt=b"fake-snapshot",
        artifact_receipt=b"fake-artifact",
        artifact_bytes=ARTIFACT_BYTES,
        artifact_target_path="src/example.py",
        source_session_id=SESSION_ID,
        task_id=TASK,
        repository=REPO,
        workstream=WORKSTREAM,
        environment="TEST",
        branch=BRANCH,
        base_sha=BASE,
        source_sha=SOURCE,
        paths=PATHS,
        subject="worker:synthetic",
        action="code",
        artifact_sha256=ARTIFACT,
    )
    values.update(changes)
    return AdmissionRequest(**values)


class WorkerAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = str(Path(self.temp.name) / "replay.sqlite")

    def tearDown(self):
        self.temp.cleanup()

    def adapter(self, verifier=None):
        return WorkerAdmissionAdapter(
            repository=REPO,
            workstream=WORKSTREAM,
            verifier=verifier,
            replay_ledger=DurableReplayLedger(self.db),
            expected_hermes_version="0.22.5",
            expected_hermes_commit=HERMES_SHA,
            expected_publisher_subject=BROKER_SUBJECT,
        )

    def reserve(self, ledger, task_id=TASK, branch=BRANCH, lease_id="lease-synthetic",
                nonce="nonce-synthetic"):
        return ledger.reserve(
            task_id=task_id, repository=REPO, workstream=WORKSTREAM,
            branch=branch, base_sha=BASE, source_sha=SOURCE,
            artifact_sha256=hashlib.sha256(ARTIFACT_BYTES).hexdigest(), lease_id=lease_id, nonce=nonce,
            context={
                "environment":"TEST", "paths":list(PATHS), "subject":"worker:synthetic",
                "issuer":"issuer:synthetic", "role":"dev-test-coder",
                "generation":2, "fence_epoch":7, "source_session_id":SESSION_ID,
                "source_path":"out/example.py", "target_path":"src/example.py",
                "artifact_size_bytes":len(ARTIFACT_BYTES),
                "hermes_version":"0.22.5", "hermes_commit":HERMES_SHA,
                "publisher_subject":BROKER_SUBJECT,
            },
        )

    def published_effect(self, task_id=TASK, branch=BRANCH):
        return PublishedEffect(
            task_id=task_id, repository=REPO, workstream=WORKSTREAM,
            branch=branch, base_sha=BASE, source_sha=SOURCE,
            artifact_sha256=hashlib.sha256(ARTIFACT_BYTES).hexdigest(), lease_id="lease-synthetic",
            commit_sha="e" * 40, pr_number=6, source_session_id=SESSION_ID,
            source_path="out/example.py", target_path="src/example.py",
            artifact_size_bytes=len(ARTIFACT_BYTES),
            producer_subject="worker:synthetic", publisher_subject=BROKER_SUBJECT,
            hermes_version="0.22.5", hermes_commit=HERMES_SHA,
            nonce="nonce-synthetic", generation=2, fence_epoch=7,
        )

    def begin_publication(self, ledger, verifier=None, now=NOW):
        return ledger.begin_publication(
            TASK, assignment_receipt=b"fake-assignment", identity_receipt=b"fake-identity",
            artifact_receipt=b"fake-artifact", artifact_bytes=ARTIFACT_BYTES,
            lease_receipt=b"fake-lease",
            guard_snapshot_receipt=b"fake-snapshot", verifier=verifier or evidence(), now=now,
        )

    def test_synthetic_exact_scope_is_contract_valid_but_performs_no_write(self):
        result = self.adapter(evidence()).admit(request(), now=NOW)
        self.assertEqual(result.code, "SCOPE_CONTRACT_VALID_SYNTHETIC_TESTS_ONLY")
        self.assertFalse(result.replay)
        self.assertFalse(result.side_effects_performed)

    def test_absent_verifier_or_receipt_fails_closed(self):
        with self.assertRaisesRegex(AdmissionDenied, "TRUST_VERIFIER_UNAVAILABLE"):
            self.adapter().admit(request(), now=NOW)
        with self.assertRaisesRegex(AdmissionDenied, "AUTHENTICATED_EVIDENCE_REQUIRED"):
            self.adapter(SyntheticVerifier()).admit(request(), now=NOW)

    def test_wrong_repository_lane_branch_or_path_fails_closed(self):
        verifier = evidence()
        for changed in (
            {"repository": "example/other"},
            {"workstream": "claude-lane"},
            {"branch": "main"},
            {"paths": ("src/../secret.txt",)},
            {"paths": ("src/unassigned.py",)},
        ):
            with self.subTest(changed=changed), self.assertRaises(AdmissionDenied):
                self.adapter(verifier).admit(request(**changed), now=NOW)

    def test_path_alias_and_file_directory_overlap_fail_closed(self):
        for paths in (
            ("src/Task.py", "src/task.py"),
            ("src/task.py", "src/task.py/output.txt"),
            ("src//task.py",),
            ("src/../task.py",),
        ):
            assignment = replace(evidence().verify_assignment(b"fake-assignment"), paths=paths)
            with self.subTest(paths=paths), self.assertRaisesRegex(AdmissionDenied, "PATH_SET_INVALID"):
                self.adapter(evidence(assignment=assignment)).admit(request(paths=paths), now=NOW)

    def test_artifact_receipt_binds_session_path_bytes_and_pinned_hermes(self):
        wrong_artifact = ArtifactProvenance(
            TASK, "SESSION-FOREIGN", "out/example.py", "src/example.py",
            len(ARTIFACT_BYTES), ARTIFACT, "worker:synthetic", "0.22.5", HERMES_SHA,
        )
        verifier = evidence()
        verifier.values[("artifact", b"fake-artifact")] = wrong_artifact
        with self.assertRaisesRegex(AdmissionDenied, "ARTIFACT_PROVENANCE_MISMATCH"):
            self.adapter(verifier).admit(request(), now=NOW)

        with self.assertRaisesRegex(AdmissionDenied, "ARTIFACT_BYTES_HASH_MISMATCH"):
            self.adapter(evidence()).admit(request(artifact_bytes=ARTIFACT_BYTES + b"altered"), now=NOW)

    def test_stale_source_or_guard_head_fails_closed(self):
        verifier = evidence(snapshot=GuardSnapshot(
            REPO, WORKSTREAM, "TEST", BRANCH, "d" * 40, 2, 7, 0, NOW,
        ))
        with self.assertRaisesRegex(AdmissionDenied, "STALE_SOURCE_SHA"):
            self.adapter(verifier).admit(request(), now=NOW)

    def test_role_escalation_and_forbidden_actions_fail_closed(self):
        elevated = replace(
            LeaseClaims("lease-synthetic", "issuer:synthetic", "worker:synthetic",
                        REPO, WORKSTREAM, "TEST", BRANCH, BASE, PATHS,
                        frozenset({"code", "admin"}), "admin",
                        NOW - timedelta(seconds=1), NOW + timedelta(minutes=4),
                        "nonce-synthetic", 2, 7),
            role="admin",
        )
        with self.assertRaisesRegex(AdmissionDenied, "LEASE_SCOPE_OR_ROLE_MISMATCH"):
            self.adapter(evidence(lease=elevated)).admit(request(), now=NOW)
        with self.assertRaisesRegex(AdmissionDenied, "ACTION_OUTSIDE_DEV_TEST_CODER_ROLE"):
            self.adapter(evidence()).admit(request(action="merge"), now=NOW)

    def test_missing_expired_and_overlong_lease_fail_closed(self):
        for lease in (
            replace(LeaseClaims("lease-synthetic", "issuer:synthetic", "worker:synthetic",
                                REPO, WORKSTREAM, "TEST", BRANCH, BASE, PATHS,
                                frozenset({"code"}), "dev-test-coder",
                                NOW - timedelta(minutes=6), NOW + timedelta(seconds=1),
                                "nonce-synthetic", 2, 7),
                    expires_at=NOW + timedelta(seconds=1)),
            replace(LeaseClaims("lease-synthetic", "issuer:synthetic", "worker:synthetic",
                                REPO, WORKSTREAM, "TEST", BRANCH, BASE, PATHS,
                                frozenset({"code"}), "dev-test-coder",
                                NOW - timedelta(seconds=1), NOW + timedelta(minutes=6),
                                "nonce-synthetic", 2, 7),
                    expires_at=NOW + timedelta(minutes=6)),
        ):
            with self.assertRaises(AdmissionDenied):
                self.adapter(evidence(lease=lease)).admit(request(), now=NOW)

    def test_snapshot_expiry_and_active_writer_collision_fail_closed(self):
        stale = GuardSnapshot(REPO, WORKSTREAM, "TEST", BRANCH, BASE, 2, 7, 0,
                              NOW - timedelta(minutes=1))
        collision = GuardSnapshot(REPO, WORKSTREAM, "TEST", BRANCH, BASE, 2, 7, 1, NOW)
        for snapshot, code in ((stale, "GUARD_SNAPSHOT_STALE"),
                               (collision, "ACTIVE_WRITER_COLLISION")):
            with self.assertRaisesRegex(AdmissionDenied, code):
                self.adapter(evidence(snapshot=snapshot)).admit(request(), now=NOW)

    def test_generation_epoch_and_identity_mismatch_fail_closed(self):
        wrong_fence = replace(
            GuardSnapshot(REPO, WORKSTREAM, "TEST", BRANCH, BASE, 2, 8, 0, NOW),
            fence_epoch=8,
        )
        with self.assertRaisesRegex(AdmissionDenied, "LEASE_FENCE_EPOCH_MISMATCH"):
            self.adapter(evidence(snapshot=wrong_fence)).admit(request(), now=NOW)
        other_identity = IdentityClaims("issuer:synthetic", "worker:other",
                                        NOW - timedelta(seconds=1), NOW + timedelta(minutes=1))
        with self.assertRaisesRegex(AdmissionDenied, "LEASE_SCOPE_OR_ROLE_MISMATCH"):
            self.adapter(evidence(identity=other_identity)).admit(request(), now=NOW)

    def test_duplicate_task_is_noop_and_changed_payload_is_rejected(self):
        adapter = self.adapter(evidence())
        first = adapter.admit(request(), now=NOW)
        replay = adapter.admit(request(), now=NOW)
        self.assertFalse(first.replay)
        self.assertTrue(replay.replay)
        changed_bytes = ARTIFACT_BYTES + b"changed"
        changed_sha = hashlib.sha256(changed_bytes).hexdigest()
        changed_verifier = evidence()
        changed_verifier.values[("artifact", b"fake-artifact")] = ArtifactProvenance(
            TASK, SESSION_ID, "out/example.py", "src/example.py", len(changed_bytes),
            changed_sha, "worker:synthetic", "0.22.5", HERMES_SHA,
        )
        with self.assertRaisesRegex(AdmissionDenied, "TASK_ID_REUSED_WITH_CHANGED_EVIDENCE"):
            WorkerAdmissionAdapter(
                repository=REPO, workstream=WORKSTREAM, verifier=changed_verifier,
                replay_ledger=DurableReplayLedger(self.db), expected_hermes_version="0.22.5",
                expected_hermes_commit=HERMES_SHA, expected_publisher_subject=BROKER_SUBJECT,
            ).admit(request(artifact_bytes=changed_bytes, artifact_sha256=changed_sha), now=NOW)

    def test_crash_restart_keeps_reservation_and_blocks_second_dispatch(self):
        first = self.adapter(evidence()).admit(request(), now=NOW)
        reopened = self.adapter(evidence()).admit(request(), now=NOW)
        self.assertFalse(first.replay)
        self.assertTrue(reopened.replay)
        self.assertFalse(reopened.side_effects_performed)

    def test_crash_after_reservation_before_publish_resumes_same_unfinished_task(self):
        ledger = DurableReplayLedger(self.db)
        self.assertTrue(self.reserve(ledger))

        # Simulate restart before the publisher was entered.
        restarted = DurableReplayLedger(self.db)
        record = restarted.get_task(TASK)
        self.assertEqual(record.state, "reserved")
        self.assertFalse(self.reserve(restarted))
        self.assertEqual(self.begin_publication(restarted), "effect_unknown")
        self.assertEqual(restarted.get_task(TASK).state, "effect_unknown")

    def test_effect_time_rechecks_lease_and_guard_before_marking_publish_attempt(self):
        ledger = self.adapter(evidence()).replay_ledger
        self.adapter(evidence()).admit(request(), now=NOW)

        expired = replace(evidence().verify_lease(b"fake-lease"), expires_at=NOW - timedelta(seconds=1))
        expired_verifier = evidence(lease=expired)
        with self.assertRaisesRegex(AdmissionDenied, "PUBLISH_GUARD_OR_LEASE_RECHECK_FAILED"):
            self.begin_publication(ledger, expired_verifier)
        self.assertEqual(ledger.get_task(TASK).state, "reserved")

        busy_guard = replace(evidence().verify_guard_snapshot(b"fake-snapshot"), active_writers=1)
        busy_verifier = evidence(snapshot=busy_guard)
        with self.assertRaisesRegex(AdmissionDenied, "PUBLISH_GUARD_OR_LEASE_RECHECK_FAILED"):
            self.begin_publication(ledger, busy_verifier)
        self.assertEqual(ledger.get_task(TASK).state, "reserved")

        foreign_artifact_verifier = evidence()
        foreign_artifact_verifier.values[("artifact", b"fake-artifact")] = replace(
            foreign_artifact_verifier.values[("artifact", b"fake-artifact")],
            source_session_id="SESSION-FOREIGN",
        )
        with self.assertRaisesRegex(AdmissionDenied, "PUBLISH_GUARD_OR_LEASE_RECHECK_FAILED"):
            self.begin_publication(ledger, foreign_artifact_verifier)
        self.assertEqual(ledger.get_task(TASK).state, "reserved")

        self.assertEqual(self.begin_publication(ledger), "effect_unknown")

    def test_publish_succeeded_but_ack_was_lost_reconciles_without_republish(self):
        ledger = DurableReplayLedger(self.db)
        self.assertTrue(self.reserve(ledger))
        self.assertEqual(self.begin_publication(ledger), "effect_unknown")

        # Simulate the remote publish succeeding before the local ACK was saved.
        restarted = DurableReplayLedger(self.db)
        self.assertEqual(restarted.get_task(TASK).state, "effect_unknown")
        with self.assertRaisesRegex(AdmissionDenied, "PUBLICATION_RECONCILIATION_REQUIRED"):
            self.begin_publication(restarted)

        verifier = SyntheticPublicationVerifier(self.published_effect())
        result = restarted.acknowledge_publication(
            TASK, b"fake-github-receipt", verifier,
        )
        self.assertEqual(result.state, "completed")
        self.assertEqual(result.commit_sha, "e" * 40)
        self.assertEqual(result.pr_number, 6)
        replayed_ack = restarted.acknowledge_publication(
            TASK, b"fake-github-receipt", verifier,
        )
        self.assertEqual(replayed_ack.state, "completed")
        self.assertFalse(self.reserve(restarted))
        self.assertEqual(restarted.get_task(TASK).state, "completed")

    def test_reserved_task_cannot_complete_from_receipt_without_publish_gate(self):
        ledger = DurableReplayLedger(self.db)
        self.assertTrue(self.reserve(ledger))
        with self.assertRaisesRegex(AdmissionDenied, "PUBLICATION_GATE_NOT_ENTERED"):
            ledger.acknowledge_publication(
                TASK, b"fake-github-receipt",
                SyntheticPublicationVerifier(self.published_effect()),
            )
        self.assertEqual(ledger.get_task(TASK).state, "reserved")

    def test_missing_or_mismatched_external_receipt_cannot_complete_task(self):
        ledger = DurableReplayLedger(self.db)
        self.reserve(ledger)
        self.begin_publication(ledger)

        with self.assertRaisesRegex(AdmissionDenied, "AUTHENTICATED_PUBLICATION_RECEIPT_REQUIRED"):
            ledger.acknowledge_publication(TASK, b"fake-github-receipt", None)
        with self.assertRaisesRegex(AdmissionDenied, "AUTHENTICATED_PUBLICATION_RECEIPT_REQUIRED"):
            ledger.acknowledge_publication(
                TASK, b"fake-github-receipt", SyntheticPublicationVerifier(None),
            )
        wrong_scope = replace(self.published_effect(), branch="lab/other-task")
        with self.assertRaisesRegex(AdmissionDenied, "PUBLICATION_RECEIPT_SCOPE_MISMATCH"):
            ledger.acknowledge_publication(
                TASK, b"fake-github-receipt", SyntheticPublicationVerifier(wrong_scope),
            )
        self.assertEqual(ledger.get_task(TASK).state, "effect_unknown")

    def test_publication_receipt_binds_hermes_session_publisher_and_fence(self):
        ledger = self.adapter(evidence()).replay_ledger
        self.adapter(evidence()).admit(request(), now=NOW)
        self.begin_publication(ledger)
        for effect in (
            replace(self.published_effect(), source_session_id="SESSION-FOREIGN"),
            replace(self.published_effect(), publisher_subject="github-broker:other"),
            replace(self.published_effect(), nonce="nonce-other"),
            replace(self.published_effect(), fence_epoch=8),
        ):
            with self.subTest(effect=effect), self.assertRaises(AdmissionDenied):
                ledger.acknowledge_publication(
                    TASK, b"fake-github-receipt", SyntheticPublicationVerifier(effect),
                )
            self.assertEqual(ledger.get_task(TASK).state, "effect_unknown")

    def test_legacy_reservation_migrates_as_unscoped_and_fails_closed(self):
        with sqlite3.connect(self.db) as db:
            db.execute("""CREATE TABLE reservations (
                task_id TEXT PRIMARY KEY, source_sha TEXT NOT NULL,
                artifact_sha256 TEXT NOT NULL, lease_id TEXT NOT NULL,
                nonce TEXT NOT NULL UNIQUE,
                state TEXT NOT NULL CHECK(state IN ('reserved'))
            )""")
            db.execute("INSERT INTO reservations VALUES (?, ?, ?, ?, ?, 'reserved')",
                       (TASK, SOURCE, ARTIFACT, "lease-synthetic", "nonce-synthetic"))

        migrated = DurableReplayLedger(self.db)
        self.assertEqual(migrated.get_task(TASK).state, "legacy_unscoped")
        with self.assertRaisesRegex(AdmissionDenied, "LEGACY_RESERVATION_SCOPE_UNTRUSTED"):
            self.begin_publication(migrated)
        with self.assertRaisesRegex(AdmissionDenied, "TASK_ID_REUSED_WITH_CHANGED_EVIDENCE"):
            self.reserve(migrated)

    def test_nonce_reuse_for_different_task_is_rejected(self):
        self.adapter(evidence()).admit(request(), now=NOW)
        changed_assignment = Assignment(
            "HERMES-WORKER-0002", REPO, WORKSTREAM, "TEST",
            "lab/task-HERMES-WORKER-0002", BASE, SOURCE, PATHS,
            "worker:synthetic", "dev-test-coder",
        )
        changed_lease = replace(LeaseClaims(
            "lease-synthetic", "issuer:synthetic", "worker:synthetic", REPO,
            WORKSTREAM, "TEST", "lab/task-HERMES-WORKER-0002", BASE, PATHS,
            frozenset({"code", "test"}), "dev-test-coder",
            NOW - timedelta(seconds=1), NOW + timedelta(minutes=4),
            "nonce-synthetic", 2, 7,
        ), lease_id="lease-other")
        changed_snapshot = GuardSnapshot(
            REPO, WORKSTREAM, "TEST", changed_assignment.branch, BASE, 2, 7, 0, NOW,
        )
        verifier = evidence(assignment=changed_assignment, lease=changed_lease,
                            snapshot=changed_snapshot)
        verifier.values[("artifact", b"fake-artifact")] = replace(
            verifier.values[("artifact", b"fake-artifact")],
            task_id=changed_assignment.task_id,
        )
        second = request(
            task_id=changed_assignment.task_id,
            branch=changed_assignment.branch,
        )
        with self.assertRaisesRegex(AdmissionDenied, "NONCE_REPLAY_OR_COLLISION"):
            self.adapter(verifier).admit(second, now=NOW)


if __name__ == "__main__":
    unittest.main()

