"""Host-only trusted context. The model receives neither issuer key nor host authority."""
import hashlib,json,os,subprocess,time
from pathlib import Path
from .one_use_lease_gate import AdmissionDenied,TrustedHostContext,HOST,canonical_json
ROOT=Path("/workspaces/.honey-hermes-authority")
PIN="9b31279911d8231e325eeb2decf17708626b8902c081d1861f35581f559d8bab"
def trusted_context(bundle):
    from cryptography.hazmat.primitives.serialization import load_pem_public_key,Encoding,PublicFormat
    if os.geteuid()!=1000 or os.environ.get("CODESPACE_NAME")!=HOST:
        raise AdmissionDenied("NOT_THE_ENROLLED_OPERATOR_HOST")
    mode=ROOT.stat();pub=(ROOT/"public.pem").read_bytes()
    if mode.st_uid!=1000 or mode.st_mode & 0o077 or hashlib.sha256(pub).hexdigest()!=PIN:
        raise AdmissionDenied("HOST_ANCHOR_PROTECTION")
    fence_check(bundle)
    e=json.loads((ROOT/"enrollment.json").read_text())
    raw=load_pem_public_key(pub).public_bytes(Encoding.Raw,PublicFormat.Raw)
    return TrustedHostContext(e["custodian"],raw,ROOT/"live-admissions.sqlite3",
        "uid:999:honey-hermes-test","uid:1000:vscode")
def fence_check(bundle):
    current=json.loads((ROOT/"current-lease.json").read_text())
    state=json.loads((ROOT/"active-fence.json").read_text())
    head=subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip()
    if canonical_json(current)!=canonical_json(bundle) or bundle["claims"]["head"]!=head:
        raise AdmissionDenied("LEASE_NOT_CURRENT_HOST_HEAD")
    if state["jti"]!=bundle["claims"]["jti"] or state["revoked"] or state["status"]!="OWNER_CONSENT_VERIFIED":
        raise AdmissionDenied("OWNER_CONSENT_OR_FENCE_NOT_READY")
    if not bundle["claims"]["issued_at"]<=int(time.time())<bundle["claims"]["expires_at"]:
        raise AdmissionDenied("EXPIRED_HOST_LEASE")
    return state["fence"]
