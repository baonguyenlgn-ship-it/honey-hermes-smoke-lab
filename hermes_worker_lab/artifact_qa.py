"""Fail-closed byte QA for Hermes LAB artifacts.

CI validates exact bytes and compiles (never executes) the artifact. A manifest
is not a signature. Authenticated intake calls validate_authenticated_artifact
with the existing WorkerAdmissionAdapter, reusing its verifier, lease/Guard
checks and durable replay ledger.
"""
from __future__ import annotations
import argparse, hashlib, json, os, py_compile, re, stat, sys, tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping
from hermes_worker_lab.worker_admission import AdmissionRequest, WorkerAdmissionAdapter, _valid_path

REPOSITORY = "baonguyenlgn-ship-it/honey-hermes-smoke-lab"
HERMES_VERSION = "0.22.5"
HERMES_COMMIT = "bf0203a794a07aac3ff764972ab9087baa4e4f4e"
SOURCE_PATH = "/opt/data/workspace/hermes_lab_record.py"
ARTIFACT_PATH = "hermes_worker_lab/artifacts/hermes_lab_record.py"
MANIFEST_PATH = "hermes_worker_lab/artifacts/hermes_lab_record.manifest.json"
MAX_BYTES = 1_048_576
FIELDS = frozenset({"task_id","source_session_id","source_path","target_path","repository",
 "workstream","environment","branch","base_sha","source_sha","paths","subject","role",
 "action","size_bytes","sha256","producer_subject","hermes_version","hermes_commit"})
SHA40 = re.compile(r"^[0-9a-f]{40}$")
SHA64 = re.compile(r"^[0-9a-f]{64}$")
TASK = re.compile(r"^[A-Z0-9][A-Z0-9-]{7,79}$")

class ArtifactQaError(ValueError):
    def __init__(self, code: str):
        super().__init__(code); self.code = code

@dataclass(frozen=True)
class ArtifactQaResult:
    size_bytes: int
    sha256: str
    task_id: str
    source_session_id: str
    status: str = "BYTES_MANIFEST_SYNTAX_PASS_PROVENANCE_UNVERIFIED"

def _safe_path(value: object) -> bool:
    # Reuse worker_admission's canonical path rules, including single backslashes.
    return isinstance(value, str) and _valid_path(value)

def _pairs(pairs: list[tuple[str,Any]]) -> dict[str,Any]:
    out={}
    for k,v in pairs:
        if k in out: raise ArtifactQaError("MANIFEST_DUPLICATE_KEY")
        out[k]=v
    return out

def parse_manifest(raw: bytes) -> dict[str,Any]:
    if len(raw)>16_384: raise ArtifactQaError("MANIFEST_SIZE_INVALID")
    try: obj=json.loads(raw.decode("utf-8"),object_pairs_hook=_pairs)
    except ArtifactQaError: raise
    except (UnicodeDecodeError,json.JSONDecodeError) as e: raise ArtifactQaError("MANIFEST_JSON_INVALID") from e
    if not isinstance(obj,dict) or set(obj)!=FIELDS: raise ArtifactQaError("MANIFEST_FIELDS_INVALID")
    return obj

def validate_manifest_bytes(manifest: Mapping[str,Any], data: bytes, *, expected_branch: str,
 expected_task_id: str|None=None, expected_source_sha: str|None=None) -> ArtifactQaResult:
    """Validate claims and exact bytes; self-reported producer/session claims remain unauthenticated."""
    if not isinstance(data,bytes) or not data: raise ArtifactQaError("ORIGINAL_BYTES_MISSING")
    if len(data)>MAX_BYTES: raise ArtifactQaError("ARTIFACT_SIZE_LIMIT_EXCEEDED")
    if not isinstance(manifest,Mapping) or set(manifest)!=FIELDS: raise ArtifactQaError("MANIFEST_FIELDS_INVALID")
    for k in FIELDS-{"paths","size_bytes"}:
        if not isinstance(manifest.get(k),str) or not manifest[k]: raise ArtifactQaError("MANIFEST_VALUE_INVALID")
    if isinstance(manifest["size_bytes"],bool) or not isinstance(manifest["size_bytes"],int):
        raise ArtifactQaError("MANIFEST_VALUE_INVALID")
    if not isinstance(manifest["paths"],list) or not manifest["paths"]: raise ArtifactQaError("MANIFEST_VALUE_INVALID")
    if not TASK.fullmatch(manifest["task_id"]): raise ArtifactQaError("TASK_ID_INVALID")
    if expected_task_id is not None and manifest["task_id"]!=expected_task_id: raise ArtifactQaError("TASK_ID_MISMATCH")
    if manifest["repository"]!=REPOSITORY: raise ArtifactQaError("REPOSITORY_SCOPE_MISMATCH")
    if manifest["branch"]!=expected_branch or manifest["environment"]!="TEST":
        raise ArtifactQaError("BRANCH_OR_ENVIRONMENT_SCOPE_MISMATCH")
    if not SHA40.fullmatch(manifest["base_sha"]) or not SHA40.fullmatch(manifest["source_sha"]):
        raise ArtifactQaError("SOURCE_PIN_INVALID")
    if expected_source_sha is not None and manifest["source_sha"]!=expected_source_sha:
        raise ArtifactQaError("SOURCE_PIN_MISMATCH")
    if manifest["source_path"]!=SOURCE_PATH: raise ArtifactQaError("SOURCE_PATH_MISMATCH")
    if manifest["target_path"]!=ARTIFACT_PATH or not _safe_path(manifest["target_path"]):
        raise ArtifactQaError("TARGET_PATH_INVALID")
    if any(not _safe_path(p) for p in manifest["paths"]) or len(set(manifest["paths"]))!=len(manifest["paths"]) or ARTIFACT_PATH not in manifest["paths"]:
        raise ArtifactQaError("PATH_SET_INVALID")
    if manifest["subject"]!=manifest["producer_subject"]: raise ArtifactQaError("PRODUCER_SUBJECT_MISMATCH")
    if manifest["role"]!="dev-test-coder" or manifest["action"]!="code": raise ArtifactQaError("ROLE_OR_ACTION_INVALID")
    if manifest["hermes_version"]!=HERMES_VERSION: raise ArtifactQaError("HERMES_VERSION_MISMATCH")
    if manifest["hermes_commit"]!=HERMES_COMMIT: raise ArtifactQaError("HERMES_COMMIT_MISMATCH")
    if not SHA64.fullmatch(manifest["sha256"]): raise ArtifactQaError("ARTIFACT_SHA_INVALID")
    if manifest["size_bytes"]!=len(data): raise ArtifactQaError("ARTIFACT_SIZE_MISMATCH")
    digest=hashlib.sha256(data).hexdigest()
    if digest!=manifest["sha256"]: raise ArtifactQaError("ARTIFACT_SHA_MISMATCH")
    return ArtifactQaResult(len(data),digest,manifest["task_id"],manifest["source_session_id"])

def validate_authenticated_artifact(manifest: Mapping[str,Any], data: bytes, *,
 adapter: WorkerAdmissionAdapter, request: AdmissionRequest, expected_branch: str,
 expected_source_sha: str, now: datetime|None=None) -> tuple[ArtifactQaResult,object]:
    """Bind original bytes to the existing authenticated admission and ledger."""
    result=validate_manifest_bytes(manifest,data,expected_branch=expected_branch,
       expected_task_id=request.task_id,expected_source_sha=expected_source_sha)
    fields={"source_session_id":request.source_session_id,"target_path":request.artifact_target_path,
      "repository":request.repository,"workstream":request.workstream,"environment":request.environment,
      "branch":request.branch,"base_sha":request.base_sha,"source_sha":request.source_sha,
      "paths":list(request.paths),"subject":request.subject,"action":request.action,
      "size_bytes":len(data),"sha256":request.artifact_sha256,"producer_subject":request.subject}
    if request.branch!=expected_branch or request.source_sha!=expected_source_sha:
        raise ArtifactQaError("ADMISSION_SOURCE_SCOPE_MISMATCH")
    if request.artifact_bytes!=data: raise ArtifactQaError("ADMISSION_BYTES_MISMATCH")
    if any(manifest.get(k)!=v for k,v in fields.items()):
        raise ArtifactQaError("ADMISSION_MANIFEST_BINDING_MISMATCH")
    return result,adapter.admit(request,now=now)

def _read_regular(path: Path, limit: int) -> bytes:
    info=path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_size>limit: raise ArtifactQaError("FILE_TYPE_OR_SIZE_INVALID")
    fd=os.open(path,os.O_RDONLY|getattr(os,"O_NOFOLLOW",0))
    try:
        chunks=[]; total=0
        while True:
            chunk=os.read(fd,min(65536,limit+1-total))
            if not chunk: break
            total+=len(chunk)
            if total>limit: raise ArtifactQaError("FILE_TYPE_OR_SIZE_INVALID")
            chunks.append(chunk)
        return b"".join(chunks)
    finally: os.close(fd)

def check_checkout(root: Path, *, expected_branch: str) -> ArtifactQaResult:
    artifact=root/ARTIFACT_PATH; manifest_path=root/MANIFEST_PATH
    has_artifact=artifact.exists() or artifact.is_symlink()
    has_manifest=manifest_path.exists() or manifest_path.is_symlink()
    if not has_artifact and not has_manifest: raise ArtifactQaError("WAITING_ORIGINAL_BYTES")
    if not has_artifact: raise ArtifactQaError("ORIGINAL_BYTES_MISSING")
    if not has_manifest: raise ArtifactQaError("MANIFEST_MISSING")
    result=validate_manifest_bytes(parse_manifest(_read_regular(manifest_path,16384)),
       _read_regular(artifact,MAX_BYTES),expected_branch=expected_branch)
    with tempfile.TemporaryDirectory(prefix="hermes-artifact-qa-") as tmp:
        py_compile.compile(str(artifact),cfile=str(Path(tmp)/"artifact.pyc"),doraise=True)
    return result

def main(argv: list[str]|None=None) -> int:
    p=argparse.ArgumentParser(); p.add_argument("--repo-root",type=Path,default=Path.cwd())
    p.add_argument("--branch",default=os.environ.get("GITHUB_HEAD_REF","")); a=p.parse_args(argv)
    try:
        if not a.branch: raise ArtifactQaError("EXPECTED_BRANCH_REQUIRED")
        r=check_checkout(a.repo_root,expected_branch=a.branch)
    except ArtifactQaError as e: print(e.code,file=sys.stderr); return 2
    except (OSError,py_compile.PyCompileError) as e:
        print(f"ARTIFACT_QA_IO_OR_COMPILE_FAILURE:{type(e).__name__}",file=sys.stderr); return 2
    print(f"ARTIFACT_QA_STATUS={r.status}")
    print(f"artifact_size_bytes={r.size_bytes}"); print(f"artifact_sha256={r.sha256}")
    print(f"task_id={r.task_id}"); print(f"source_session_id={r.source_session_id}")
    return 0

if __name__=="__main__": raise SystemExit(main())
