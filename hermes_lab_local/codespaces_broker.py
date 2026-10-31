"""Codespaces TRUSTED publisher: only the existing Hermes LAB PR branch.

This file must run as the Codespace's normal GitHub-authenticated operator, NEVER
as the unprivileged Hermes worker. Original source comes from a protected
Codespaces directory and is treated as untrusted input until AST/SHA validation.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from hermes_lab_local.verify_artifact import gate

REPO="baonguyenlgn-ship-it/honey-hermes-smoke-lab"
BRANCH="hermes-lab/actions-publisher-20261029-01"
SRC="hermes_lab_local/generated/normalize_label.py"
RECEIPT="hermes_lab_local/generated/provenance.json"
ROOT=Path("/workspaces/.honey-hermes-test/inbox/task-01/verified")

def validate(source: bytes, manifest: bytes)->dict:
    if not isinstance(source,bytes) or not (1<=len(source)<=2048):
        raise ValueError("SOURCE_BYTES_BOUND")
    if not isinstance(manifest,bytes) or len(manifest)>4096:
        raise ValueError("MANIFEST_BYTES_BOUND")
    try: metadata=json.loads(manifest)
    except (ValueError,UnicodeDecodeError) as e: raise ValueError("MANIFEST_JSON_INVALID") from e
    if not isinstance(metadata,dict) or metadata.get("schema")!="hermes.isolated.original-source.v1":
        raise ValueError("WRONG_SOURCE_MANIFEST")
    for key in ("origin_cloud_authenticated","core_authorized","production","human_qa"):
        if metadata.get(key) is not False:
            raise ValueError("FORGED_AUTHORITY_"+key)
    if metadata.get("size")!=len(source) or metadata.get("sha256")!=hashlib.sha256(source).hexdigest():
        raise ValueError("SOURCE_SIZE_SHA_MISMATCH")
    if metadata.get("hermes_sha")!="bf0203a794a07aac3ff764972ab9087baa4e4f4e":
        raise ValueError("UPSTREAM_HERMES_PIN_CHANGED")
    text=source.decode("utf8")
    if gate(text)!=source:
        raise ValueError("NONCANONICAL_ORIGINAL_SOURCE")
    return {
        "schema":"honey.hermes.codespaces.original-local-claim.v1",
        "sha256":metadata["sha256"],"size":len(source),
        "upstream_hermes_sha":metadata["hermes_sha"],
        "provider_origin_signed":False,
        "external_worker_identity_verified":False,
        "core_guard_authorized":False,
        "merge_authorized":False,
        "production_authorized":False
    }

def command(*argv):
    return subprocess.check_output(argv,stderr=subprocess.DEVNULL,text=True).strip()

def private_file(name):
    # Fixed paths only; source is not any command-line user-supplied path.
    return subprocess.check_output(("sudo","-n","cat",str(ROOT/name)),stderr=subprocess.DEVNULL)

def main():
    if os.environ.get("CODESPACES")!="true":
        raise SystemExit("CODESPACES_ONLY")
    work=Path(__file__).resolve().parents[1]
    if command("git","-C",str(work),"branch","--show-current")!=BRANCH:
        raise SystemExit("BROKER_NOT_IN_ALLOWED_BRANCH")
    remote=command("git","-C",str(work),"remote","get-url","origin")
    if remote not in ("https://github.com/"+REPO,"https://github.com/"+REPO+".git","git@github.com:"+REPO+".git"):
        raise SystemExit("BROKER_WRONG_REPO")
    if command("git","-C",str(work),"status","--porcelain"):
        raise SystemExit("BROKER_DIRTY_WORKTREE")
    local=command("git","-C",str(work),"rev-parse","HEAD")
    refs=command("git","-C",str(work),"ls-remote","origin","refs/heads/"+BRANCH)
    if not refs or refs.split()[0]!=local:
        raise SystemExit("BROKER_REMOTE_LEASE_STALE")
    if (work/SRC).exists() or (work/RECEIPT).exists():
        raise SystemExit("BROKER_ARTIFACT_ALREADY_EXISTS")
    source=private_file("normalize_label.py")
    meta=private_file("manifest.json")
    receipt=validate(source,meta)
    # All validations complete. Only two exact TEST files may be written.
    dest=work/SRC
    dest.parent.mkdir(parents=True,exist_ok=True)
    with dest.open("xb") as out: out.write(source)
    with (work/RECEIPT).open("x",encoding="utf8") as out:
        out.write(json.dumps(receipt,sort_keys=True)+"\n")
    try:
        subprocess.check_call(("git","-C",str(work),"add","--",SRC,RECEIPT))
        subprocess.check_call(("git","-C",str(work),"-c","core.hooksPath=/dev/null",
          "-c","user.name=Honey Hermes LAB Broker",
          "-c","user.email=hermes-lab-broker@users.noreply.github.com",
          "commit","-m","test: stage locally verified Hermes TEST source only"))
        # Default non-force push rejects a changed branch head. No automatic retry.
        subprocess.check_call(("git","-C",str(work),"push","origin","HEAD:refs/heads/"+BRANCH))
    except subprocess.CalledProcessError:
        raise SystemExit("BROKER_EFFECT_UNKNOWN_DO_NOT_RETRY_RECONCILE_REMOTE_SHA")
    print("HERMES_CODESPACES_BROKER_LAB_PUSHED_NO_PRODUCTION_RIGHTS "+receipt["sha256"])

if __name__=="__main__":
    main()
