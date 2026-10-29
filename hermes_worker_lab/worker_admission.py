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


class EvidenceVerifier(Protocol):
    """Provider/Guard trust adapter; implementations must authenticate bytes."""

    def verify_assignment(self, receipt: bytes) -> Assignment | None: ...
    def verify_identity(self, receipt: bytes) -> IdentityClaims | None: ...
    def verify_lease(self, receipt: bytes) -> LeaseClaims | None: ...
    def verify_guard_snapshot(self, receipt: bytes) -> GuardSnapshot | None: ...


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
    """Local idempotency aid for the offline contract, not a Guard nonce store."""

    def __init__(self, database_path: str):
        self.database_path = database_path
        with self._connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("""CREATE TABLE IF NOT EXISTS reservations (
                task_id TEXT PRIMARY KEY,
                source_sha TEXT NOT NULL,
                artifact_sha256 TEXT NOT NULL,
                lease_id TEXT NOT NULL,
                nonce TEXT NOT NULL UNIQUE,
                state TEXT NOT NULL CHECK(state IN ('reserved'))
            )""")

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.database_path, timeout=5, isolation_level=None)
        db.row_factory = sqlite3.Row
        return db

    def reserve(self, *, task_id: str, source_sha: str, artifact_sha256: str,
                lease_id: str, nonce: str) -> bool:
        """Return False for an exact replay; raise on changed/reused identifiers."""
        db = self._connect()
        try:
            db.execute("BEGIN IMMEDIATE")
            existing = db.execute(
                "SELECT source_sha, artifact_sha256, lease_id, nonce FROM reservations WHERE task_id=?",
                (task_id,),
            ).fetchone()
            if existing:
                exact = (existing["source_sha"] == source_sha
                         and existing["artifact_sha256"] == artifact_sha256
                         and existing["lease_id"] == lease_id
                         and existing["nonce"] == nonce)
                db.execute("COMMIT")
                if exact:
                    return False
                raise AdmissionDenied("TASK_ID_REUSED_WITH_CHANGED_EVIDENCE")
            try:
                db.execute(
                    "INSERT INTO reservations VALUES (?, ?, ?, ?, ?, 'reserved')",
                    (task_id, source_sha, artifact_sha256, lease_id, nonce),
                )
            except sqlite3.IntegrityError as exc:
                db.execute("ROLLBACK")
                raise AdmissionDenied("NONCE_REPLAY_OR_COLLISION") from exc
            db.execute("COMMIT")
            return True
        finally:
            db.close()


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

