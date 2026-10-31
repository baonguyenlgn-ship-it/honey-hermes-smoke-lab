"""Independently verify downloaded *original* Hermes model source artifact.

This validates actual source bytes + manifest, not the success of upload alone.
No model inference, no generated replacement and no GitHub write action.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from .e1_durable_new_task import (
    ISOLATED_BRANCH, TASK_ID, PREDECESSOR_RUN,
    qa_new_e1_task,
)
from .windows_local_hermes_coding import PINNED_HERMES

EXPECTED_KEYS = frozenset({
    "schema", "task_id", "evidence_kind", "source_filename",
    "source_sha256", "source_bytes", "source_branch", "source_commit",
    "github_run_id", "predecessor_windows_run", "model_attempts",
    "repairs", "model", "hermes_upstream_sha", "qa",
    "independent_download_qa", "signed_gate_b",
    "production_authorized", "unattended_dispatch_proven",
})

class ArtifactVerificationFailed(RuntimeError):
    pass

def verify_original_artifact(folder: Path, *, sha: str, run_id: int) -> dict:
    if not folder.is_dir() or folder.is_symlink():
        raise ArtifactVerificationFailed("E1_MISSING_OR_SYMLINK_ARTIFACT")
    paths = {x.name: x for x in folder.iterdir()}
    if (set(paths) != {"original_model_generated.py", "manifest.json"}
            or any(not p.is_file() or p.is_symlink() for p in paths.values())):
        raise ArtifactVerificationFailed("E1_ARTIFACT_FILES_UNEXPECTED")
    manifest_path = paths["manifest.json"]
    if not 20 <= manifest_path.stat().st_size <= 4096:
        raise ArtifactVerificationFailed("E1_MANIFEST_BOUNDS_INVALID")
    try:
        m = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (ValueError, UnicodeError, OSError):
        raise ArtifactVerificationFailed("E1_MANIFEST_NOT_PARSEABLE") from None
    if not isinstance(m, dict) or set(m) != EXPECTED_KEYS:
        raise ArtifactVerificationFailed("E1_MANIFEST_SCHEMA_INVALID")
    if (m["schema"] != "honey.hermes.real-model-durable-evidence.v1"
            or m["task_id"] != TASK_ID
            or m["source_filename"] != "original_model_generated.py"
            or m["source_branch"] != ISOLATED_BRANCH
            or m["source_commit"] != sha
            or type(m["github_run_id"]) is not int or m["github_run_id"] != run_id
            or type(m["predecessor_windows_run"]) is not int or m["predecessor_windows_run"] != PREDECESSOR_RUN
            or m["evidence_kind"] != "UNSIGNED_ISOLATED_LOOPBACK_TEST"
            or m["hermes_upstream_sha"] != PINNED_HERMES
            or m["model"] != "local-loopback-Qwen2.5-Coder-1.5B"
            or m["qa"] != "AST_ALLOWLIST_PLUS_BEHAVIOR"
            or m["independent_download_qa"] != "PENDING"
            or m["signed_gate_b"] is not False
            or m["production_authorized"] is not False
            or m["unattended_dispatch_proven"] is not False
            or type(m["model_attempts"]) is not int or not 1 <= m["model_attempts"] <= 3
            or type(m["repairs"]) is not int or m["repairs"] != m["model_attempts"] - 1
            or type(m["source_bytes"]) is not int or not 40 <= m["source_bytes"] <= 2048
            or not isinstance(m["source_sha256"], str) or len(m["source_sha256"]) != 64
            or any(x not in "0123456789abcdef" for x in m["source_sha256"])):
        raise ArtifactVerificationFailed("E1_MODEL_OR_RUN_OR_SCOPE_NOT_MATCHED")
    try:
        raw = paths["original_model_generated.py"].read_bytes()
        text = raw.decode("utf-8", errors="strict")
    except (OSError, UnicodeError):
        raise ArtifactVerificationFailed("E1_ORIGINAL_BYTES_NOT_UTF8") from None
    if (len(raw) != m["source_bytes"]
            or hashlib.sha256(raw).hexdigest() != m["source_sha256"]):
        raise ArtifactVerificationFailed("E1_ORIGINAL_SOURCE_SHA256_MISMATCH")
    try:
        approved = qa_new_e1_task(text)
    except Exception:
        raise ArtifactVerificationFailed("E1_DOWNLOADED_CODE_FAILED_INDEPENDENT_QA") from None
    if approved != raw:
        raise ArtifactVerificationFailed("E1_SOURCE_BYTES_CHANGED_IN_QA")
    return {
        "status": "HERMES_E1_INDEPENDENT_GITHUB_WINDOWS_DOWNLOADED_ORIGINAL_QA_PASS",
        "github_run_id": run_id,
        "source_commit": sha,
        "task_id": TASK_ID,
        "original_source_sha256": m["source_sha256"],
        "original_bytes": len(raw),
        "model_attempts": m["model_attempts"],
        "repairs": m["repairs"],
        "source_only_replay": False,
        "signed_gate_b": False,
        "event_wakeup_proven": False,
        "github_source_writer_proven": False,
    }

def main():
    folder = Path(os.environ["HERMES_E1_DOWNLOADED_ARTIFACT"]).resolve(strict=True)
    sha = os.environ["GITHUB_SHA"]
    run_id = int(os.environ["GITHUB_RUN_ID"])
    result = verify_original_artifact(folder, sha=sha, run_id=run_id)
    print(json.dumps(result, sort_keys=True), flush=True)

if __name__ == "__main__":
    main()
