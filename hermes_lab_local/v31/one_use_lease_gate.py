"""TEST-only signed one-use mission lease verifier.

NOT a lease issuer; NOT a Hermes runner; NOT deployable without an independent
trusted host custodian, externally pinned public key and protected SQLite store.
Keep the trust anchor and store OUTSIDE source-controlled/untrusted directories.
"""
from __future__ import annotations

import base64
import os
import stat
import binascii
import json
import re
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

REPO = "baonguyenlgn-ship-it/honey-hermes-smoke-lab"
BRANCH = "hermes-lab/actions-publisher-20261029-01"
TASK = "LAB-NORMALIZE-REPAIR-V1"
MODEL = "upstage/solar-mini4:free"
HOST = "dreadful-wraith-6v5gr7w9x9r7c6rj"
AUDIENCE = "honey.hermes.lab-one-use-admission.v1"
OUTPUT_PATHS = (
    "hermes_lab_local/repair_generated/normalize_label.py",
    "hermes_lab_local/repair_generated/receipt.json",
)
LEASE_KEYS = frozenset({
    "aud", "issuer", "jti", "repo", "pr", "branch", "head", "host_id",
    "task_id", "mission_comment_id", "mission_nonce", "worker_actor",
    "broker_actor", "model", "max_repairs", "allowed_paths", "issued_at",
    "expires_at", "cost_policy", "mode",
})
REQUIRED_TICKET_KEYS = frozenset({
    "comment_id", "nonce", "expected_head", "task_id", "status",
    "authorized_for_execution", "production_authorized", "core_guard_authorized",
})
SHA_RE = re.compile(r"[a-f0-9]{40}\Z")


class AdmissionDenied(ValueError):
    """One missing or invalid trust requirement must stop execution."""


@dataclass(frozen=True)
class TrustedHostContext:
    """Supplied ONLY by an independently authenticated host operator.

    Never load public_key / custodian_id / state_db from Hermes prompts,
    GitHub comments, a candidate artifact or the model subprocess.
    """
    custodian_id: str
    public_key_ed25519: bytes
    state_db: Path
    worker_actor: str
    broker_actor: str
    host_id: str = HOST


def canonical_json(value: Mapping) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def _reject(message: str) -> None:
    raise AdmissionDenied(message)


def verify_signed_lease(bundle: Mapping, ticket: Mapping,
                        host: TrustedHostContext, *, now: int | None = None) -> dict:
    """Verify externally signed TEST lease without executing or minting it.

    Function does not assert real custodian existence; caller must establish
    custodian identity and secure source of the pinned public key out-of-band.
    """
    if not isinstance(host, TrustedHostContext):
        _reject("TRUSTED_HOST_CONTEXT_REQUIRED")
    if not isinstance(host.public_key_ed25519, bytes) or len(host.public_key_ed25519) != 32:
        _reject("PINNED_PUBLIC_KEY_MISSING")
    if not isinstance(host.custodian_id, str) or not host.custodian_id.strip():
        _reject("CUSTODIAN_NOT_IDENTIFIED")
    if (not isinstance(host.worker_actor, str) or not host.worker_actor.strip()
            or not isinstance(host.broker_actor, str) or not host.broker_actor.strip()
            or host.worker_actor == host.broker_actor):
        _reject("SEPARATE_WORKER_AND_BROKER_REQUIRED")
    if not isinstance(bundle, dict) or set(bundle) != {"claims", "sig_b64"}:
        _reject("INVALID_SIGNED_BUNDLE")
    claims = bundle.get("claims")
    if not isinstance(claims, dict) or set(claims) != LEASE_KEYS:
        _reject("INVALID_LEASE_FIELDS")
    if not isinstance(ticket, dict) or not REQUIRED_TICKET_KEYS.issubset(ticket):
        _reject("UNVERIFIED_MISSION_TICKET")
    # A dry-run ticket is *never* direct permission; only a separately signed
    # lease from the authenticated external custodian is an admission candidate.
    if ticket["status"] != "LAB_TASK_RECEIVED_NOT_RUNNING" or any(
        ticket[k] is not False for k in
        ("authorized_for_execution", "core_guard_authorized", "production_authorized")
    ):
        _reject("NOT_THE_VERIFIED_DRY_RUN_INTAKE")
    if not isinstance(bundle["sig_b64"], str):
        _reject("MISSING_SIGNATURE")
    try:
        signature = base64.b64decode(bundle["sig_b64"], validate=True)
        if len(signature) != 64:
            _reject("INVALID_SIGNATURE_SIZE")
        Ed25519PublicKey.from_public_bytes(host.public_key_ed25519).verify(
            signature, canonical_json(claims))
    except (InvalidSignature, ValueError, binascii.Error, TypeError):
        _reject("CUSTODIAN_SIGNATURE_UNVERIFIED")

    if (claims["aud"] != AUDIENCE or claims["issuer"] != host.custodian_id
            or claims["repo"] != REPO or claims["pr"] != 4
            or type(claims["pr"]) is not int
            or claims["branch"] != BRANCH or claims["host_id"] != host.host_id
            or claims["task_id"] != TASK or claims["model"] != MODEL
            or claims["mode"] != "test-lab-once"
            or claims["cost_policy"] != "no-new-billable-service"
            or claims["worker_actor"] != host.worker_actor
            or claims["broker_actor"] != host.broker_actor):
        _reject("LEASE_SCOPE_MISMATCH")
    if (not isinstance(claims["head"], str) or not SHA_RE.fullmatch(claims["head"])
            or claims["head"] != ticket["expected_head"]
            or claims["task_id"] != ticket["task_id"]
            or type(claims["mission_comment_id"]) is not int
            or claims["mission_comment_id"] != ticket["comment_id"]
            or claims["mission_nonce"] != ticket["nonce"]):
        _reject("STALE_HEAD_OR_MISSION_MISMATCH")
    if (type(claims["max_repairs"]) is not int or claims["max_repairs"] != 2
            or type(claims["allowed_paths"]) is not list
            or claims["allowed_paths"] != list(OUTPUT_PATHS)):
        _reject("REPAIR_OR_PATH_SCOPE_MISMATCH")
    if (type(claims["issued_at"]) is not int or type(claims["expires_at"]) is not int):
        _reject("INVALID_EXPIRY_TYPE")
    instant = int(time.time()) if now is None else now
    if (type(instant) is not int or instant < claims["issued_at"]
            or instant >= claims["expires_at"]
            or claims["expires_at"] - claims["issued_at"] > 900):
        _reject("LEASE_EXPIRED_FUTURE_OR_TOO_LONG")
    if (not isinstance(claims["jti"], str)
            or not re.fullmatch(r"[A-Za-z0-9_-]{20,90}", claims["jti"])):
        _reject("INVALID_LEASE_ID")
    return claims.copy()


def claim_once(bundle: Mapping, ticket: Mapping, host: TrustedHostContext, *,
               now: int | None = None) -> dict:
    """Fail-closed, durable exactly-once *admission* (NOT execution).

    An interrupted claim remains claimed. Re-use must be refused until an
    externally authorized custodian recovery process, intentionally absent.
    """
    claims = verify_signed_lease(bundle, ticket, host, now=now)
    db = host.state_db
    if not isinstance(db, Path) or not db.is_absolute() or not db.parent.is_dir():
        _reject("PROTECTED_LEDGER_NOT_CONFIGURED")
    # Require local protected ledger directory/file. Operator additionally must
    # verify storage durability, custodian identity, revocation and host custody.
    try:
        parent_stat = os.lstat(db.parent)
        if (not stat.S_ISDIR(parent_stat.st_mode) or parent_stat.st_uid != os.geteuid()
                or stat.S_IMODE(parent_stat.st_mode) & 0o077):
            _reject("LEDGER_PARENT_NOT_PROTECTED")
        if os.path.lexists(db):
            file_stat = os.lstat(db)
            if (not stat.S_ISREG(file_stat.st_mode)
                    or file_stat.st_uid != os.geteuid()
                    or stat.S_IMODE(file_stat.st_mode) & 0o177
                    or file_stat.st_nlink != 1):
                _reject("LEDGER_FILE_NOT_PROTECTED")
        else:
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
            if hasattr(os, "O_NOFOLLOW"):
                flags |= os.O_NOFOLLOW
            try:
                fd = os.open(db, flags, 0o600)
            except FileExistsError:
                # Other parallel consumer created it. Revalidate on next call,
                # not before a fresh check to avoid a write through a symlink.
                _reject("LEDGER_CONCURRENT_INIT_RETRY_WITH_FRESH_READBACK")
            else:
                os.close(fd)
    except OSError:
        _reject("LEDGER_PROTECTION_UNVERIFIED")
    try:
        con = sqlite3.connect(str(db), timeout=4, isolation_level=None)
        try:
            con.execute("PRAGMA busy_timeout=4000")
            con.execute("PRAGMA synchronous=FULL")
            con.execute("BEGIN IMMEDIATE")
            con.execute("""CREATE TABLE IF NOT EXISTS admissions (
                jti TEXT PRIMARY KEY, mission_nonce TEXT UNIQUE NOT NULL,
                comment_id INTEGER UNIQUE NOT NULL, head TEXT NOT NULL,
                admitted_at INTEGER NOT NULL, status TEXT NOT NULL
            )""")
            con.execute("""INSERT INTO admissions
                (jti, mission_nonce, comment_id, head, admitted_at, status)
                VALUES (?, ?, ?, ?, ?, 'CLAIMED_NOT_EXECUTED')""",
                (claims["jti"], claims["mission_nonce"], claims["mission_comment_id"],
                 claims["head"], int(time.time()) if now is None else now))
            con.execute("COMMIT")
        except Exception:
            try:
                con.execute("ROLLBACK")
            except sqlite3.Error:
                pass
            raise
        finally:
            con.close()
    except sqlite3.IntegrityError:
        _reject("REPLAY_OR_ALREADY_CLAIMED")
    except (OSError, sqlite3.Error):
        _reject("LEDGER_UNAVAILABLE_FAIL_CLOSED")
    return {
        "status": "CLAIMED_NOT_EXECUTED",
        "jti": claims["jti"],
        "mission_comment_id": claims["mission_comment_id"],
        "expected_head": claims["head"],
        "permitted_to_publish": False,
        "permitted_to_access_core": False,
        "live_hermes_model_proven": False,
    }
