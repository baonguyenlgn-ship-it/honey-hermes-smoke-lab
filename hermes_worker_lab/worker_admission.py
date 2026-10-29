"""Fail-closed, offline contract for a future isolated coding worker.

This module is deliberately not a Honey/Core publisher. It has no network
client, signing key, token parser, GitHub API, or deployment path. A production
adapter must supply an independently reviewed verifier for assignment,
identity, lease, and live Guard-state receipts before this contract can allow a
scope. The test verifier in the companion tests is synthetic only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import PurePosixPath
import hashlib
import re
import sqlite3
from typing import Protocol


MAX_LEASE_TTL = timedelta(minutes=5)
MAX_GUARD_AGE = timedelta(seconds=30)
ALLOWED_ENVIRONMENTS = frozenset({"DEV", "TEST"})
ALLOWED_ACTIONS = frozenset({"code", "test", "branch-create", "commit", "draft-pr"})
DENIED_ACTIONS = frozenset({
    "merge", "production-write", "production-deploy", "policy-change",
    "secret-read", "admin", "root", "customer-send", "payment",
})
_SHA40 = re.compile(r"^[0-9a-f]{40}$")
_SHA64 = re.compile(r"^[0-9a-f]{64}$")
_TASK_ID = re.compile(r"^[A-Z0-9][A-Z0-9-]{7,79}$")


class AdmissionDenied(ValueError):
    """A fail-closed policy decision with a non-secret reason code."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class Assignment:
    task_id: str
    repository: str
    workstream: str
    environment: str
    branch: str
    base_sha: str
    source_sha: str
    paths: tuple[str, ...]
    subject: str
    role: str


@dataclass(frozen=True)
class IdentityClaims:
    issuer: str
    subject: str
    issued_at: datetime
    expires_at: datetime


@dataclass(frozen=True)
class LeaseClaims:
    lease_id: str
    issuer: str
    subject: str
    repository: str
    workstream: str
    environment: str
    branch: str
    base_sha: str
    paths: tuple[str, ...]
    actions: frozenset[str]
    role: str
    issued_at: datetime
    expires_at: datetime
    nonce: str
    generation: int
    fence_epoch: int


@dataclass(frozen=True)
class GuardSnapshot:
    repository: str
    workstream: str
    environment: str
    branch: str
    head_sha: str
    generation: int
    fence_epoch: int
    active_writers: int
    captured_at: datetime


@dataclass(frozen=True)
class PublishedEffect:
    """Claims extracted from an externally authenticated publish receipt."""

    task_id: str
    repository: str
    workstream: str
    branch: str
    base_sha: str
    source_sha: str
    artifact_sha256: str
    lease_id: str
    commit_sha: str
    pr_number: int


@dataclass(frozen=True)
class TaskRecord:
    task_id: str
    state: str
    commit_sha: str | None = None
    pr_number: int | None = None
    receipt_sha256: str | None = None


class EvidenceVerifier(Protocol):
    """Provider/Guard trust adapter; implementations must authenticate bytes."""

    def verify_assignment(self, receipt: bytes) -> Assignment | None: ...
    def verify_identity(self, receipt: bytes) -> IdentityClaims | None: ...
    def verify_lease(self, receipt: bytes) -> LeaseClaims | None: ...
    def verify_guard_snapshot(self, receipt: bytes) -> GuardSnapshot | None: ...


class PublicationVerifier(Protocol):
    """Independent verifier for a canonical external publication receipt."""

    def verify_publication(self, receipt: bytes) -> PublishedEffect | None: ...


@dataclass(frozen=True)
class AdmissionRequest:
    assignment_receipt: bytes = field(repr=False)
    identity_receipt: bytes = field(repr=False)
    lease_receipt: bytes = field(repr=False)
    guard_snapshot_receipt: bytes = field(repr=False)
    task_id: str
    repository: str
    workstream: str
    environment: str
    branch: str
    base_sha: str
    source_sha: str
    paths: tuple[str, ...]
    subject: str
    action: str
    artifact_sha256: str


@dataclass(frozen=True)
class AdmissionDecision:
    code: str
    task_id: str
    replay: bool
    side_effects_performed: bool = False


def _aware(value: datetime) -> bool:
    return value.tzinfo is not None and value.utcoffset() is not None


def _valid_path(path: str) -> bool:
    if not path or "\\" in path or path.startswith("/"):
        return False
    parts = PurePosixPath(path).parts
    return all(part not in {"", ".", ".."} for part in parts)


class DurableReplayLedger:
    """Local recovery ledger, not a publisher or canonical Guard nonce store."""

    def __init__(self, database_path: str):
        self.database_path = database_path
        db = self._connect()
        try:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("BEGIN IMMEDIATE")
            exists = db.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name='reservations'"
            ).fetchone()
            schema = (exists["sql"] or "").lower() if exists else ""
            if exists and not all(token in schema for token in (
                    "repository", "workstream", "branch", "base_sha",
                    "effect_unknown", "completed", "published_commit_sha")):
                columns = {row["name"] for row in db.execute("PRAGMA table_info(reservations)")}
                db.execute("DROP TABLE IF EXISTS reservations_next")
                self._create_table(db, "reservations_next")
                if {"task_id", "source_sha", "artifact_sha256", "lease_id", "nonce"}.issubset(columns):
                    db.execute("""INSERT INTO reservations_next
                        (task_id, repository, workstream, branch, base_sha, source_sha,
                         artifact_sha256, lease_id, nonce, state)
                        SELECT task_id, '', '', '', '', source_sha, artifact_sha256,
                               lease_id, nonce, 'legacy_unscoped' FROM reservations""")
                db.execute("DROP TABLE reservations")
                db.execute("ALTER TABLE reservations_next RENAME TO reservations")
            elif not exists:
                self._create_table(db, "reservations")
            db.execute("COMMIT")
        except Exception:
            if db.in_transaction:
                db.execute("ROLLBACK")
            raise
        finally:
            db.close()

    @staticmethod
    def _create_table(db: sqlite3.Connection, name: str) -> None:
        db.execute(f"""CREATE TABLE {name} (
            task_id TEXT PRIMARY KEY,
            repository TEXT NOT NULL,
            workstream TEXT NOT NULL,
            branch TEXT NOT NULL,
            base_sha TEXT NOT NULL,
            source_sha TEXT NOT NULL,
            artifact_sha256 TEXT NOT NULL,
            lease_id TEXT NOT NULL,
            nonce TEXT NOT NULL UNIQUE,
            state TEXT NOT NULL CHECK(state IN
                ('reserved', 'effect_unknown', 'completed', 'legacy_unscoped')),
            published_commit_sha TEXT,
            published_pr_number INTEGER,
            publication_receipt_sha256 TEXT
        )""")

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.database_path, timeout=5, isolation_level=None)
        db.row_factory = sqlite3.Row
        return db

    def reserve(self, *, task_id: str, repository: str, workstream: str,
                branch: str, base_sha: str, source_sha: str, artifact_sha256: str,
                lease_id: str, nonce: str) -> bool:
        """Return False for an exact replay; raise on changed/reused identifiers."""
        db = self._connect()
        try:
            db.execute("BEGIN IMMEDIATE")
            existing = db.execute(
                """SELECT repository, workstream, branch, base_sha, source_sha,
                          artifact_sha256, lease_id, nonce, state
                   FROM reservations WHERE task_id=?""",
                (task_id,),
            ).fetchone()
            if existing:
                exact = (existing["repository"] == repository
                         and existing["workstream"] == workstream
                         and existing["branch"] == branch
                         and existing["base_sha"] == base_sha
                         and existing["source_sha"] == source_sha
                         and existing["artifact_sha256"] == artifact_sha256
                         and existing["lease_id"] == lease_id
                         and existing["nonce"] == nonce
                         and existing["state"] != "legacy_unscoped")
                db.execute("COMMIT")
                if exact:
                    return False
                raise AdmissionDenied("TASK_ID_REUSED_WITH_CHANGED_EVIDENCE")
            try:
                db.execute(
                    """INSERT INTO reservations
                    (task_id, repository, workstream, branch, base_sha, source_sha,
                     artifact_sha256, lease_id, nonce, state)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'reserved')""",
                    (task_id, repository, workstream, branch, base_sha, source_sha,
                     artifact_sha256, lease_id, nonce),
                )
            except sqlite3.IntegrityError as exc:
                db.execute("ROLLBACK")
                raise AdmissionDenied("NONCE_REPLAY_OR_COLLISION") from exc
            db.execute("COMMIT")
            return True
        finally:
            db.close()

    def get_task(self, task_id: str) -> TaskRecord | None:
        db = self._connect()
        try:
            row = db.execute(
                """SELECT task_id, state, published_commit_sha, published_pr_number,
                          publication_receipt_sha256 FROM reservations WHERE task_id=?""",
                (task_id,),
            ).fetchone()
        finally:
            db.close()
        if row is None:
            return None
        return TaskRecord(row["task_id"], row["state"], row["published_commit_sha"],
                          row["published_pr_number"], row["publication_receipt_sha256"])

    def begin_publication(self, task_id: str) -> str:
        """Fence one publish attempt; unknown outcome requires receipt reconciliation."""
        db = self._connect()
        try:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT state FROM reservations WHERE task_id=?", (task_id,)).fetchone()
            if row is None:
                raise AdmissionDenied("TASK_RESERVATION_NOT_FOUND")
            state = row["state"]
            if state == "reserved":
                db.execute("UPDATE reservations SET state='effect_unknown' WHERE task_id=?", (task_id,))
                db.execute("COMMIT")
                return "effect_unknown"
            if state == "completed":
                db.execute("COMMIT")
                return state
            if db.in_transaction:
                db.execute("ROLLBACK")
            raise AdmissionDenied("PUBLICATION_RECONCILIATION_REQUIRED" if state == "effect_unknown"
                                  else "LEGACY_RESERVATION_SCOPE_UNTRUSTED")
        finally:
            db.close()

    def acknowledge_publication(self, task_id: str, receipt: bytes,
                                verifier: PublicationVerifier | None) -> TaskRecord:
        """Mark complete only after an external verifier authenticates matching GitHub facts."""
        if verifier is None:
            raise AdmissionDenied("AUTHENTICATED_PUBLICATION_RECEIPT_REQUIRED")
        effect = verifier.verify_publication(receipt)
        if effect is None:
            raise AdmissionDenied("AUTHENTICATED_PUBLICATION_RECEIPT_REQUIRED")
        if (not _SHA40.fullmatch(effect.commit_sha)
                or not isinstance(effect.pr_number, int)
                or isinstance(effect.pr_number, bool)
                or effect.pr_number < 1):
            raise AdmissionDenied("PUBLICATION_RECEIPT_INVALID")
        receipt_sha256 = hashlib.sha256(receipt).hexdigest()
        db = self._connect()
        try:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                """SELECT repository, workstream, branch, base_sha, source_sha,
                          artifact_sha256, lease_id, state, published_commit_sha,
                          published_pr_number, publication_receipt_sha256
                   FROM reservations WHERE task_id=?""",
                (task_id,),
            ).fetchone()
            if row is None:
                raise AdmissionDenied("TASK_RESERVATION_NOT_FOUND")
            matches = (effect.task_id == task_id
                       and effect.repository == row["repository"]
                       and effect.workstream == row["workstream"]
                       and effect.branch == row["branch"]
                       and effect.base_sha == row["base_sha"]
                       and effect.source_sha == row["source_sha"]
                       and effect.artifact_sha256 == row["artifact_sha256"]
                       and effect.lease_id == row["lease_id"])
            if not matches:
                raise AdmissionDenied("PUBLICATION_RECEIPT_SCOPE_MISMATCH")
            if row["state"] == "legacy_unscoped":
                raise AdmissionDenied("LEGACY_RESERVATION_SCOPE_UNTRUSTED")
            if row["state"] == "completed":
                exact = (row["published_commit_sha"] == effect.commit_sha
                         and row["published_pr_number"] == effect.pr_number
                         and row["publication_receipt_sha256"] == receipt_sha256)
                if not exact:
                    raise AdmissionDenied("COMPLETION_RECEIPT_CONFLICT")
                db.execute("COMMIT")
            else:
                db.execute(
                    """UPDATE reservations SET state='completed', published_commit_sha=?,
                       published_pr_number=?, publication_receipt_sha256=? WHERE task_id=?""",
                    (effect.commit_sha, effect.pr_number, receipt_sha256, task_id),
                )
                db.execute("COMMIT")
        except Exception:
            if db.in_transaction:
                db.execute("ROLLBACK")
            raise
        finally:
            db.close()
        record = self.get_task(task_id)
        assert record is not None
        return record


class WorkerAdmissionAdapter:
    """Validate a candidate scope; never executes or publishes the task."""

    def __init__(self, *, repository: str, workstream: str,
                 verifier: EvidenceVerifier | None,
                 replay_ledger: DurableReplayLedger):
        self.repository = repository
        self.workstream = workstream
        self.verifier = verifier
        self.replay_ledger = replay_ledger

    def admit(self, request: AdmissionRequest, *, now: datetime | None = None) -> AdmissionDecision:
        instant = now or datetime.now(timezone.utc)
        if not _aware(instant):
            raise AdmissionDenied("CLOCK_MUST_BE_TIMEZONE_AWARE")
        if self.verifier is None:
            raise AdmissionDenied("TRUST_VERIFIER_UNAVAILABLE")
        assignment = self.verifier.verify_assignment(request.assignment_receipt)
        identity = self.verifier.verify_identity(request.identity_receipt)
        lease = self.verifier.verify_lease(request.lease_receipt)
        snapshot = self.verifier.verify_guard_snapshot(request.guard_snapshot_receipt)
        if any(item is None for item in (assignment, identity, lease, snapshot)):
            raise AdmissionDenied("AUTHENTICATED_EVIDENCE_REQUIRED")

        assert assignment is not None and identity is not None
        assert lease is not None and snapshot is not None
        if request.action in DENIED_ACTIONS or request.action not in ALLOWED_ACTIONS:
            raise AdmissionDenied("ACTION_OUTSIDE_DEV_TEST_CODER_ROLE")
        if request.environment not in ALLOWED_ENVIRONMENTS:
            raise AdmissionDenied("ENVIRONMENT_NOT_DEV_TEST")
        if request.repository != self.repository or request.workstream != self.workstream:
            raise AdmissionDenied("ADAPTER_SCOPE_MISMATCH")
        if not _TASK_ID.fullmatch(request.task_id):
            raise AdmissionDenied("TASK_ID_INVALID")
        if not _SHA40.fullmatch(request.base_sha) or not _SHA40.fullmatch(request.source_sha):
            raise AdmissionDenied("SOURCE_SHA_INVALID")
        if not _SHA64.fullmatch(request.artifact_sha256):
            raise AdmissionDenied("ARTIFACT_SHA_INVALID")
        if not request.paths or len(set(request.paths)) != len(request.paths):
            raise AdmissionDenied("PATH_SET_INVALID")
        if any(not _valid_path(path) for path in request.paths):
            raise AdmissionDenied("PATH_SET_INVALID")
        if request.branch in {"main", "master"} or request.branch.startswith("production/"):
            raise AdmissionDenied("PROTECTED_BRANCH_DENIED")

        expected = (assignment.task_id, assignment.repository, assignment.workstream,
                    assignment.environment, assignment.branch, assignment.base_sha,
                    assignment.source_sha, assignment.paths, assignment.subject,
                    assignment.role)
        actual = (request.task_id, request.repository, request.workstream,
                  request.environment, request.branch, request.base_sha,
                  request.source_sha, tuple(request.paths), request.subject,
                  "dev-test-coder")
        if expected != actual:
            raise AdmissionDenied("ASSIGNMENT_BINDING_MISMATCH")

        scopes = (lease.repository == request.repository
                  and lease.workstream == request.workstream
                  and lease.environment == request.environment
                  and lease.branch == request.branch
                  and lease.base_sha == request.base_sha
                  and tuple(lease.paths) == tuple(request.paths)
                  and lease.subject == request.subject
                  and identity.subject == request.subject
                  and assignment.subject == request.subject
                  and identity.issuer == lease.issuer
                  and lease.role == "dev-test-coder"
                  and assignment.role == "dev-test-coder"
                  and request.action in lease.actions
                  and lease.actions.issubset(ALLOWED_ACTIONS))
        if not scopes:
            raise AdmissionDenied("LEASE_SCOPE_OR_ROLE_MISMATCH")
        if not all(_aware(t) for t in (identity.issued_at, identity.expires_at,
                                       lease.issued_at, lease.expires_at,
                                       snapshot.captured_at)):
            raise AdmissionDenied("EVIDENCE_TIME_INVALID")
        if identity.issued_at > instant or identity.expires_at <= instant:
            raise AdmissionDenied("IDENTITY_EXPIRED_OR_NOT_YET_VALID")
        if lease.issued_at > instant or lease.expires_at <= instant:
            raise AdmissionDenied("LEASE_EXPIRED_OR_NOT_YET_VALID")
        if lease.expires_at <= lease.issued_at or lease.expires_at - lease.issued_at > MAX_LEASE_TTL:
            raise AdmissionDenied("LEASE_TTL_EXCEEDS_POLICY")
        if snapshot.captured_at > instant or instant - snapshot.captured_at > MAX_GUARD_AGE:
            raise AdmissionDenied("GUARD_SNAPSHOT_STALE")
        if (snapshot.repository != request.repository or snapshot.workstream != request.workstream
                or snapshot.environment != request.environment or snapshot.branch != request.branch):
            raise AdmissionDenied("GUARD_SNAPSHOT_SCOPE_MISMATCH")
        if snapshot.head_sha != request.base_sha or request.source_sha != assignment.source_sha:
            raise AdmissionDenied("STALE_SOURCE_SHA")
        if snapshot.generation != lease.generation or snapshot.fence_epoch != lease.fence_epoch:
            raise AdmissionDenied("LEASE_FENCE_EPOCH_MISMATCH")
        if snapshot.active_writers != 0:
            raise AdmissionDenied("ACTIVE_WRITER_COLLISION")
        if not lease.lease_id or not lease.nonce or lease.generation < 1 or lease.fence_epoch < 1:
            raise AdmissionDenied("LEASE_ID_NONCE_OR_FENCE_MISSING")

        new_task = self.replay_ledger.reserve(
            task_id=request.task_id,
            repository=request.repository,
            workstream=request.workstream,
            branch=request.branch,
            base_sha=request.base_sha,
            source_sha=request.source_sha,
            artifact_sha256=request.artifact_sha256,
            lease_id=lease.lease_id,
            nonce=lease.nonce,
        )
        return AdmissionDecision(
            code="SCOPE_CONTRACT_VALID_SYNTHETIC_TESTS_ONLY",
            task_id=request.task_id,
            replay=not new_task,
            side_effects_performed=False,
        )

