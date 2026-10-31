"""Trusted Codespace operator only: one source/receipt LAB push, no provider or Core access."""
import hashlib,json,os,subprocess
from pathlib import Path
from hermes_lab_local.repair_loop import qa,QaFailure,TASK,MODEL,HERMES_SHA
REPO="baonguyenlgn-ship-it/honey-hermes-smoke-lab"
BRANCH="hermes-lab/actions-publisher-20261029-01"
ROOT=Path("/workspaces/.honey-hermes-test/inbox/repair-loop-01")
SRC="hermes_lab_local/repair_generated/normalize_label.py"
RECEIPT="hermes_lab_local/repair_generated/receipt.json"

def validate(source,raw_receipt):
    if not source or len(source)>2048 or len(raw_receipt)>8192: raise ValueError("ARTIFACT_SIZE_BOUND")
    try: r=json.loads(raw_receipt); text=source.decode("utf8")
    except (ValueError,UnicodeDecodeError): raise ValueError("INVALID_ARTIFACT") from None
    fields={"schema","task_id","model","hermes_sha","status","attempts","repairs","qa_events",
            "provider_origin_signed","core_guard_authorized","production_authorized",
            "merge_authorized","automatic_unattended_mode","sha256","size"}
    if not isinstance(r,dict) or set(r)!=fields: raise ValueError("RECEIPT_FIELDS_CHANGED")
    if r["schema"]!="honey.hermes.bounded-repair-lab.v1" or r["task_id"]!=TASK or r["model"]!=MODEL or r["hermes_sha"]!=HERMES_SHA or r["status"]!="QA_PASS":
        raise ValueError("WRONG_TASK_OR_FREE_MODEL")
    if any(r[x] is not False for x in ("provider_origin_signed","core_guard_authorized","production_authorized","merge_authorized","automatic_unattended_mode")):
        raise ValueError("FORGED_AUTHORITY")
    a=r["attempts"]
    if type(a)!=int or not 1<=a<=3 or type(r["repairs"])!=int or r["repairs"]!=a-1: raise ValueError("REPAIR_LIMIT")
    journal=r["qa_events"]
    if not isinstance(journal,list) or len(journal)!=a: raise ValueError("JOURNAL_COUNT")
    for i,x in enumerate(journal):
        if not isinstance(x,dict) or set(x)!={"attempt","status","detail"} or x["attempt"]!=i+1: raise ValueError("JOURNAL_INVALID")
        if i<a-1 and (x["status"]!="QA_REJECTED" or x["detail"] not in ("BAD_UTF8","OVERSIZE","MISSING_FUNCTION","UNSAFE_AST","BAD_BEHAVIOR")):
            raise ValueError("REPAIR_FEEDBACK_INVALID")
        if i==a-1 and (x["status"]!="QA_PASS" or x["detail"]!=r["sha256"]): raise ValueError("NO_FINAL_PASS")
    try: checked=qa(text)
    except QaFailure: raise ValueError("SOURCE_UNSAFE_AST") from None
    if checked!=source or r["size"]!=len(source) or hashlib.sha256(source).hexdigest()!=r["sha256"]:
        raise ValueError("SOURCE_SHA_MISMATCH")
    return r

def git(*args):
    return subprocess.check_output(("git",*args),text=True,stderr=subprocess.DEVNULL).strip()

def main():
    if os.environ.get("CODESPACES")!="true" or os.getuid()==0 or os.environ.get("USER")=="honey-hermes-test":
        raise SystemExit("TRUSTED_CODESPACE_OPERATOR_ONLY")
    root=Path(__file__).resolve().parents[1]
    if git("-C",str(root),"branch","--show-current")!=BRANCH: raise SystemExit("WRONG_BRANCH")
    url=git("-C",str(root),"remote","get-url","origin")
    if url not in (f"https://github.com/{REPO}",f"https://github.com/{REPO}.git",f"git@github.com:{REPO}.git"):
        raise SystemExit("WRONG_REPO")
    if git("-C",str(root),"status","--porcelain"): raise SystemExit("DIRTY_LOCAL_WORKTREE")
    sha=git("-C",str(root),"rev-parse","HEAD")
    remote=git("-C",str(root),"ls-remote","origin","refs/heads/"+BRANCH)
    if not remote or remote.split()[0]!=sha: raise SystemExit("REMOTE_SHA_MOVED")
    if (root/SRC).exists() or (root/RECEIPT).exists(): raise SystemExit("DUPLICATE_TASK_REFUSED")
    source=subprocess.check_output(("sudo","-n","cat",str(ROOT/"candidate.py")),stderr=subprocess.DEVNULL)
    raw=subprocess.check_output(("sudo","-n","cat",str(ROOT/"receipt.json")),stderr=subprocess.DEVNULL)
    receipt=validate(source,raw)
    dest=root/SRC;dest.parent.mkdir(exist_ok=True)
    with dest.open("xb") as f:f.write(source)
    publish={"schema":"honey.hermes.lab-repair-readback.v1","task_id":TASK,"model":MODEL,
             "sha256":receipt["sha256"],"size":receipt["size"],"attempts":receipt["attempts"],
             "repairs":receipt["repairs"],"hermes_sha":HERMES_SHA,
             "provider_origin_signed":False,"core_guard_authorized":False,
             "production_authorized":False,"unattended_execution_authorized":False}
    with (root/RECEIPT).open("x",encoding="utf8") as f:f.write(json.dumps(publish,sort_keys=True)+"\n")
    try:
        subprocess.check_call(("git","-C",str(root),"add","--",SRC,RECEIPT))
        subprocess.check_call(("git","-C",str(root),"-c","user.name=Honey Hermes TEST Broker",
          "-c","user.email=hermes-test-broker@users.noreply.github.com","commit",
          "-m","test: publish bounded Hermes result for independent Windows QA"))
        subprocess.check_call(("git","-C",str(root),"push","origin","HEAD:refs/heads/"+BRANCH))
    except subprocess.CalledProcessError:
        raise SystemExit("BROKER_EFFECT_UNKNOWN_RECONCILE_REMOTE_BEFORE_RETRY")
    print("HERMES_TEST_BROKER_PUSHED_PENDING_WINDOWS_QA_SHA="+receipt["sha256"])
if __name__=="__main__":main()
