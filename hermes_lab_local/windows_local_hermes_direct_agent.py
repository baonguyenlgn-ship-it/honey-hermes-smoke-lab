"""Genuine pinned upstream Hermes AIAgent (no gateway) on Windows loopback CPU.

One NEW isolated normalize_sku task. Actual local GGUF inference is required,
independent AST/Unicode QA and at most 2 QA-triggered real model repair turns.
Every subprocess is transient, provider keys are fake loopback-only, no GitHub
write, paid route, publisher, Codespace issuer, or claimed Gate-B execution.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

from .windows_local_hermes_coding import qa_original_source, QaRejected, PINNED_HERMES

MODEL = "local-qwen"
LOCAL_BASE = "http://127.0.0.1:18081/v1"
MAX_REPAIRS = 2
WORKER_TIMEOUT = 125

def actual_model_turn(prompt: str, attempt: int, source: Path, temp: Path) -> str:
    request = temp / f"private-direct-request-{attempt}.txt"
    response = temp / f"private-direct-response-{attempt}.json"
    request.write_text(prompt, encoding="utf8")
    env = os.environ.copy()
    for name in ("GITHUB_TOKEN","GH_TOKEN","GITHUB_PAT","NOUS_API_KEY",
                 "OPENAI_API_KEY","ANTHROPIC_API_KEY","OPENROUTER_API_KEY"):
        env.pop(name, None)
    env["HERMES_DIRECT_REQUEST"] = str(request)
    env["HERMES_DIRECT_RESPONSE"] = str(response)
    env["PYTHONPATH"] = os.pathsep.join((str(source), str(Path(__file__).resolve().parents[1])))
    executable = env.get("HERMES_PYTHON", "python")
    try:
        result = subprocess.run(
            [executable, "-m", "hermes_lab_local.windows_local_hermes_direct_agent", "--worker"],
            cwd=source, env=env, capture_output=True,
            timeout=WORKER_TIMEOUT, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        raise RuntimeError("DIRECT_HERMES_MODEL_OUTCOME_UNKNOWN_NO_RETRY") from None
    if result.returncode:
        if response.exists() and response.stat().st_size < 4096:
            try:
                v = json.loads(response.read_text(encoding="utf8"))
                code = str(v.get("error_class", "UNKNOWN"))[:80]
                if code.isidentifier():
                    print("HERMES_DIRECT_UPSTREAM_FAILURE_CLASS=" + code)
            except (OSError, ValueError):
                pass
        raise RuntimeError("DIRECT_HERMES_MODEL_FAILED_NO_BLIND_RETRY")
    if not response.is_file() or response.stat().st_size > 8192:
        raise RuntimeError("DIRECT_HERMES_OUTPUT_MISSING_OR_OVER_BUDGET")
    try:
        v = json.loads(response.read_text(encoding="utf8"))
        if v.get("status") != "ACTUAL_MODEL_RESPONSE" or not isinstance(v.get("source"), str):
            raise ValueError()
        return v["source"]
    except (ValueError, OSError, KeyError):
        raise RuntimeError("DIRECT_HERMES_OUTPUT_INVALID_NO_RETRY") from None

def worker() -> None:
    response = Path(os.environ["HERMES_DIRECT_RESPONSE"])
    request = Path(os.environ["HERMES_DIRECT_REQUEST"])
    try:
        from run_agent import AIAgent
        # This is the actual upstream agent, NOT an imitated model or mocked
        # provider. It targets only loopback and can do at most one iteration.
        agent = AIAgent(
            base_url=LOCAL_BASE, api_key="local-fixture-not-secret",
            provider="custom", api_mode="chat_completions",
            model=MODEL, max_iterations=1, max_tokens=220,
            enabled_toolsets=[], disabled_toolsets=[
                "terminal","file","browser","web","memory","mcp",
                "delegation","cron","automation","github",
            ],
            save_trajectories=False, verbose_logging=False,
            quiet_mode=True, skip_context_files=True, skip_memory=True,
            skip_background_review=True, fallback_model={},
            run_budget_seconds=100,
        )
        result = agent.run_conversation(request.read_text(encoding="utf8"))
        if not isinstance(result, dict) or result.get("failed"):
            code = str(result.get("failure_reason") if isinstance(result,dict) else "INVALID_RESULT")
            response.write_text(json.dumps({
                "status":"PROVIDER_FAILED",
                "error_class": code[:70].replace(" ", "_"),
            }), encoding="utf8")
            raise SystemExit(2)
        text = result.get("final_response")
        if not isinstance(text,str) or not text.strip() or len(text.encode("utf8"))>2048:
            response.write_text(json.dumps({
                "status":"EMPTY_OR_OVERSIZE", "error_class":"NO_REAL_SOURCE",
            }),encoding="utf8")
            raise SystemExit(2)
        response.write_text(json.dumps({
            "status":"ACTUAL_MODEL_RESPONSE", "source":text,
        },ensure_ascii=False),encoding="utf8")
    except SystemExit:
        raise
    except Exception as error:
        response.write_text(json.dumps({
            "status":"AGENT_EXCEPTION", "error_class":type(error).__name__,
        }),encoding="utf8")
        raise SystemExit(2) from None

def main() -> None:
    source = Path(os.environ["HERMES_UPSTREAM_SOURCE"]).resolve()
    temp = Path(os.environ["RUNNER_TEMP"]).resolve() / "hermes-direct-local"
    temp.mkdir(mode=0o700,exist_ok=False)
    actual=subprocess.check_output(["git","-C",str(source),"rev-parse","HEAD"],
                                   text=True).strip()
    if actual != PINNED_HERMES:
        raise RuntimeError("HERMES_UPSTREAM_PIN_CHANGED")
    prompt = (
        "Write ONLY Python code (no Markdown or commentary), defining one "
        "function normalize_sku(value). Convert input to str, strip leading "
        "and trailing whitespace, uppercase with Unicode support, and replace "
        "every remaining ASCII space character with a hyphen. No imports, "
        "comments, network access or other functions."
    )
    for attempt in range(MAX_REPAIRS+1):
        print("HERMES_GENUINE_AIAgent_LOCAL_MODEL_ATTEMPT="+str(attempt+1), flush=True)
        source_code = actual_model_turn(prompt,attempt,source,temp)
        try:
            checked = qa_original_source(source_code)
        except QaRejected as error:
            reason=str(error)
            print("HERMES_GENUINE_MODEL_INDEPENDENT_QA_REJECT="+reason,flush=True)
            if attempt >= MAX_REPAIRS:
                raise RuntimeError("HERMES_GENUINE_MODEL_REPAIR_LIMIT_EXHAUSTED")
            prompt=(
                "Your Python function failed independent QA with code "+reason+
                ". Correct it. Define exactly: def normalize_sku(value): "
                "return str(value).strip().upper().replace(' ', '-'). "
                "Output ONLY Python source without formatting or extra text."
            )
            continue
        print(json.dumps({
            "status":"ACTUAL_HERMES_AIAgent_LOCAL_MODEL_QA_PASS",
            "origin":"NousResearch/hermes-agent pinned source direct AIAgent",
            "upstream_sha":PINNED_HERMES,
            "model":"local-qwen-gguf", "external_provider_calls":0,
            "sha256":hashlib.sha256(checked).hexdigest(),
            "size":len(checked),"attempts":attempt+1,"repairs":attempt,
            "signed_codespace_gate_b":False, "automatic_next_task":False,
            "github_source_writes":False,
        },sort_keys=True),flush=True)
        return
    raise RuntimeError("UNREACHABLE")

if __name__=="__main__":
    if sys.argv[1:] == ["--worker"]:
        worker()
    else:
        main()
