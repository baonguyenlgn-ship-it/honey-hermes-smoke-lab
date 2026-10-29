"""Credential-free validation for a future Hermes LAB GitHub handoff.

This module does not authenticate to GitHub, read secrets, create refs, or open
pull requests. It validates an artifact and non-secret authorization claims
before a separately approved publisher can perform those operations.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import re
from typing import Mapping, Sequence


REPOSITORY = "baonguyenlgn-ship-it/honey-hermes-smoke-lab"
REQUIRED_PERMISSIONS = frozenset({"contents:write", "pull_requests:write"})
ALLOWED_PERMISSIONS = REQUIRED_PERMISSIONS | {"metadata:read"}
MAX_AUTH_TTL = timedelta(minutes=10)
_SHA40 = re.compile(r"^[0-9a-f]{40}$")
_SHA64 = re.compile(r"^[0-9a-f]{64}$")
_TASK_ID = re.compile(r"^[A-Z0-9][A-Z0-9-]{7,79}$")
_SAFE_BASENAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_GITHUB_TOKEN = re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,})\b")
_PEM_BLOCK = re.compile(
    r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----.*?-----END [A-Z0-9 ]*PRIVATE KEY-----",
    re.DOTALL,
)


class HandoffError(ValueError):
    """Base class for a fail-closed handoff rejection."""


class ArtifactMismatch(HandoffError):
    pass


class AuthorizationRejected(HandoffError):
    pass


class PublicationConflict(HandoffError):
    pass


@dataclass(frozen=True)
class ArtifactManifest:
    task_id: str
    source_session: str
    source_sha: str
    file_name: str
    size_bytes: int
    sha256: str
    branch: str
    base_sha: str


@dataclass(frozen=True)
class AuthorizationClaims:
    """Non-secret facts supplied by a trusted credential broker.

    A token or private key must never be passed to this object or this module.
    `issued_at` and `expires_at` must come from the broker's authenticated
    response; this value object cannot establish that provenance itself.
    """

    repository: str
    permissions: frozenset[str]
    issued_at: datetime
    expires_at: datetime
    issuer: str


@dataclass(frozen=True)
class PublicationRecord:
    task_id: str
    source_session: str
    artifact_sha256: str
    commit_sha: str


@dataclass(frozen=True)
class PublicationDecision:
    action: str  # "create" or "already_published"
    branch: str


def validate_authorization(
    claims: AuthorizationClaims,
    *,
    repository: str = REPOSITORY,
    now: datetime | None = None,
) -> None:
    """Require a live, exact-repository grant with a maximum 10-minute TTL."""
    instant = now or datetime.now(timezone.utc)
    if any(
        timestamp.tzinfo is None
        for timestamp in (instant, claims.issued_at, claims.expires_at)
    ):
        raise AuthorizationRejected("authorization timestamps must include a timezone")
    if claims.repository != repository:
        raise AuthorizationRejected("authorization is not restricted to the LAB repository")
    if not REQUIRED_PERMISSIONS.issubset(claims.permissions):
        raise AuthorizationRejected("authorization lacks a required LAB write permission")
    if not claims.permissions.issubset(ALLOWED_PERMISSIONS):
        raise AuthorizationRejected("authorization grants permissions beyond the LAB minimum")
    if claims.issued_at > instant:
        raise AuthorizationRejected("authorization issue time is in the future")
    if claims.expires_at <= instant:
        raise AuthorizationRejected("authorization has expired")
    if claims.expires_at <= claims.issued_at:
        raise AuthorizationRejected("authorization expiry must follow its issue time")
    if claims.expires_at - claims.issued_at > MAX_AUTH_TTL:
        raise AuthorizationRejected("authorization TTL exceeds the 10-minute LAB policy")
    if not claims.issuer.strip():
        raise AuthorizationRejected("authorization issuer is missing")


def verify_artifact(
    payload: bytes,
    manifest: ArtifactManifest,
    *,
    expected_task_id: str,
    expected_source_session: str,
    expected_source_sha: str,
    expected_base_sha: str,
) -> str:
    """Verify bytes and fence task, source, base, filename and target branch."""
    if not isinstance(payload, bytes):
        raise ArtifactMismatch("artifact payload must be bytes")
    if not _TASK_ID.fullmatch(manifest.task_id) or manifest.task_id != expected_task_id:
        raise ArtifactMismatch("task id does not match the authorized task")
    if (
        not expected_source_session.strip()
        or not manifest.source_session.strip()
        or manifest.source_session != expected_source_session
    ):
        raise ArtifactMismatch("source session does not match the assigned Hermes session")
    if not _SHA40.fullmatch(manifest.source_sha) or manifest.source_sha != expected_source_sha:
        raise ArtifactMismatch("source SHA does not match the pinned source")
    if not _SHA40.fullmatch(manifest.base_sha) or manifest.base_sha != expected_base_sha:
        raise ArtifactMismatch("base SHA changed; refresh the checkpoint before publishing")
    if not _SAFE_BASENAME.fullmatch(manifest.file_name) or manifest.file_name in {".", ".."}:
        raise ArtifactMismatch("artifact filename must be a safe basename")
    if manifest.size_bytes != len(payload):
        raise ArtifactMismatch("artifact size does not match the manifest")
    if not _SHA64.fullmatch(manifest.sha256):
        raise ArtifactMismatch("manifest SHA-256 is malformed")
    actual_sha = hashlib.sha256(payload).hexdigest()
    if actual_sha != manifest.sha256:
        raise ArtifactMismatch("artifact SHA-256 does not match the manifest")
    expected_branch = f"hermes-lab/task-{expected_task_id}"
    if manifest.branch != expected_branch:
        raise ArtifactMismatch("target branch is outside the task-specific LAB fence")
    return actual_sha


def decide_publication(
    manifest: ArtifactManifest,
    *,
    artifact_sha256: str,
    existing_task: PublicationRecord | None,
    existing_branch_commit: str | None,
) -> PublicationDecision:
    """Prevent duplicate publication and refuse to move an occupied branch."""
    if existing_task is not None:
        if (
            existing_task.task_id == manifest.task_id
            and existing_task.source_session == manifest.source_session
            and existing_task.artifact_sha256 == artifact_sha256
            and _SHA40.fullmatch(existing_task.commit_sha)
        ):
            if existing_branch_commit != existing_task.commit_sha:
                raise PublicationConflict("task record and branch ref disagree; refusing replay")
            return PublicationDecision("already_published", manifest.branch)
        raise PublicationConflict("task id is already bound to different publication data")
    if existing_branch_commit is not None:
        raise PublicationConflict("task branch already exists; refusing to overwrite its ref")
    return PublicationDecision("create", manifest.branch)


def redact_secrets(text: str, secret_values: Sequence[str] = ()) -> str:
    """Redact known values, GitHub token forms and PEM private-key blocks."""
    redacted = _PEM_BLOCK.sub("[REDACTED PRIVATE KEY]", text)
    redacted = _GITHUB_TOKEN.sub("[REDACTED GITHUB TOKEN]", redacted)
    for secret in sorted((s for s in secret_values if s), key=len, reverse=True):
        redacted = redacted.replace(secret, "[REDACTED SECRET]")
    return redacted
