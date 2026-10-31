"""Hermes LAB bounded real one-shot + up to TWO QA-triggered repair turns.

No automatic publication, Core authority or provider-origin signature. A real provider
failure ends the run immediately. The provider is fixed to Nous FREE model.
"""
from __future__ import annotations
import ast, hashlib, json, os, re, subprocess
from pathlib import Path
from hermes_lab_local.codespaces_stream_gate import terminal_source

TASK="hermes-lab-rename-label-v1"
MODEL="upstage/solar-mini4:free"
HERMES_SHA="bf0203a794a07aac3ff764972ab9087baa4e4f4e"
ROOT=Path("/workspaces/.honey-hermes-test")
SOURCE=ROOT/"source/hermes-agent"
OUTPUT=ROOT/"inbox/repair-loop-01"
EXPECTED="def normalize_label(text):\n    return str(text).strip().casefold()"
MAX_REPAIRS=2

class ProviderError(Exception): pass
class QaFailure(Exception): pass

def qa(source):
    if not isinstance(source,str): raise QaFailure("BAD_UTF8")
    b=source.encode("utf8")
    if not (20<=len(b)<=2048) or any(x in source for x in ("\x00","\r","\ufeff","#")):
        raise QaFailure("OVERSIZE")
    try: tree=ast.parse(source)
    except (SyntaxError,ValueError): raise QaFailure("UNSAFE_AST") from None
    if len(tree.body)!=1 or not isinstance(tree.body[0],ast.FunctionDef):
        raise QaFailure("MISSING_FUNCTION")
    if ast.dump(tree,include_attributes=False)!=ast.dump(ast.parse(EXPECTED),include_attributes=False):
        raise QaFailure("UNSAFE_AST")
    # Only exact side-effect-free AST is executable; never execute arbitrary AI output.
    env={"__builtins__":{"str":str}}
    exec(compile(tree,"<pinned-private-lab-qa>","exec"),env)
    f=env["normalize_label"]
    for x,y in (("  Xoài Cát Chu  ","xoài cát chu"),(" BƯỞI ","bưởi"),
      ("  Coconut  ","coconut"),(" 안녕하세요 ","안녕하세요"),(" 芒果 ","芒果"),
      ("Straße","strasse"),("İ","i\u0307"),(123,"123"),(None,"none"),(" ","")):
        if f(x)!=y: raise QaFailure("BAD_BEHAVIOR")
    return b

def prompt(attempt,reason):
    q=("Hermes LAB: return ONLY Python code defining one function normalize_label(text). "
       "Convert text to str, strip surrounding whitespace and Unicode-casefold. "
       "No comments/imports/Markdown/extra text. Only public example data.")
    return q+((" Independent QA rejected previous code: "+reason+". Correct the code.") if attempt else "")

def run_loop(infer,events=None):
    """Pure, bounded orchestrator; injected fake inference may test state only."""
    journal=[] if events is None else events
    feedback=""
    for attempt in range(3):
        answer=infer(prompt(attempt,feedback),attempt) # Provider errors NEVER retried.
        try: b=qa(answer)
        except QaFailure as e:
            feedback=str(e) if str(e) in ("BAD_UTF8","OVERSIZE","MISSING_FUNCTION","UNSAFE_AST","BAD_BEHAVIOR") else "UNSAFE_AST"
            journal.append({"attempt":attempt+1,"status":"QA_REJECTED","detail":feedback})
            if attempt==MAX_REPAIRS:
                return {"status":"QA_EXHAUSTED","attempts":3,"repairs":2},None
            continue
        sha=hashlib.sha256(b).hexdigest()
        journal.append({"attempt":attempt+1,"status":"QA_PASS","detail":sha})
        return {"status":"QA_PASS","attempts":attempt+1,"repairs":attempt,"sha256":sha,"size":len(b)},b
    raise AssertionError("BAD_LOOP")

def infer_real(text,attempt):
    request=OUTPUT/f"attempt-{attempt}-request.txt"
    stream=OUTPUT/f"attempt-{attempt}-private.jsonl"
    stderr=OUTPUT/f"attempt-{attempt}-diagnostics-private.log"
    request.write_text(text,encoding="utf8")
    cmd=["python",str(SOURCE/"hermes"),"chat","--query-file",str(request),"--oneshot",
         "--format","stream-json","--max-turns","1","--provider","nous",
         "--model",MODEL,"--ignore-rules"]
    with stream.open("xb") as out,stderr.open("xb") as err:
        try: result=subprocess.run(cmd,cwd=ROOT/"sandbox",stdout=out,stderr=err,timeout=90,check=False)
        except subprocess.TimeoutExpired: raise ProviderError("PROVIDER_TIMEOUT_NO_RETRY") from None
    if result.returncode: raise ProviderError("PROVIDER_EXIT_NONZERO_NO_RETRY")
    if stream.stat().st_size>65536: raise ProviderError("STREAM_OVER_BUDGET")
    try: return terminal_source(stream.read_text(encoding="utf8"))
    except (ValueError,UnicodeDecodeError,json.JSONDecodeError):
        raise ProviderError("PROVIDER_STREAM_INVALID_NO_RETRY") from None

def preflight():
    if os.environ.get("CODESPACES")!="true" or os.getuid()==0 or os.environ.get("USER")!="honey-hermes-test":
        raise ProviderError("TEST_CODESPACE_UID_ONLY")
    if os.environ.get("HERMES_HOME")!=str(ROOT/"home/.hermes"):
        raise ProviderError("WRONG_PRIVATE_HERMES_HOME")
    if any(os.environ.get(k) for k in ("GITHUB_TOKEN","GH_TOKEN","GITHUB_PAT","OPENAI_API_KEY","ANTHROPIC_API_KEY")):
        raise ProviderError("PRIVILEGED_ENV_PRESENT")
    if not (SOURCE/".git").is_dir(): raise ProviderError("HERMES_NOT_INSTALLED")
    if subprocess.check_output(["git","-C",str(SOURCE),"rev-parse","HEAD"],text=True).strip()!=HERMES_SHA:
        raise ProviderError("HERMES_SHA_MISMATCH")
    cfg=(ROOT/"home/.hermes/config.yaml")
    if not cfg.is_file(): raise ProviderError("NO_PROVIDER_CONFIG")
    config=cfg.read_text(encoding="utf8")
    if MODEL not in config or "provider: nous" not in config or "disabled_toolsets" not in config:
        raise ProviderError("FREE_MODEL_OR_TOOL_LOCK_MISSING")
    tools=subprocess.run(["python",str(SOURCE/"hermes"),"tools","list"],capture_output=True,text=True,timeout=20)
    if tools.returncode or "disabled  terminal" not in tools.stdout or re.search(r"✓.*enabled",tools.stdout):
        raise ProviderError("TOOLS_NOT_DISABLED")

def receipt(result,source,events):
    meta={"schema":"honey.hermes.bounded-repair-lab.v1","task_id":TASK,
          "model":MODEL,"hermes_sha":HERMES_SHA,"status":result["status"],
          "attempts":result["attempts"],"repairs":result["repairs"],"qa_events":events,
          "provider_origin_signed":False,"core_guard_authorized":False,
          "production_authorized":False,"merge_authorized":False,
          "automatic_unattended_mode":False}
    if source is not None:
        (OUTPUT/"candidate.py").write_bytes(source)
        meta.update(sha256=hashlib.sha256(source).hexdigest(),size=len(source))
    (OUTPUT/"receipt.json").write_text(json.dumps(meta,sort_keys=True)+"\n",encoding="utf8")

def main():
    preflight()
    os.umask(0o077)
    OUTPUT.mkdir(mode=0o700,exist_ok=False)
    events=[]
    try: result,source=run_loop(infer_real,events)
    except ProviderError as e:
        (OUTPUT/"provider_status.json").write_text(json.dumps({"status":"PROVIDER_BLOCKED","code":str(e)})+"\n")
        raise SystemExit("HERMES_PROVIDER_BLOCKED_NO_RETRY")
    receipt(result,source,events)
    if source is None: raise SystemExit("HERMES_2_REPAIRS_EXHAUSTED_NO_PUBLISH")
    print("HERMES_REAL_LAB_PRIVATE_QA_PASS_SHA="+result["sha256"])

if __name__=="__main__": main()
