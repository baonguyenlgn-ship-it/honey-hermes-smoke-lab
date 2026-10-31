"""E1: one NEW local-only Hermes-generated source artifact with independent readback.

Not a rerun of C/D, not Codespace-signed Gate B, not an event dispatcher.
No customer data, repo writer, model credentials, external paid services, or
authority granted by the public GitHub artifact. This program persists only
new LAB model bytes after an independent, bounded AST+behavior QA PASS.
"""
from __future__ import annotations

import ast
import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess
import urllib.request

from .approved_task_discovery import read_only_live_discovery
from .low_stock_semantic_qa import _body
from .strict_model_code_envelope import strict_python_envelope
from .windows_local_hermes_coding import PINNED_HERMES, QaRejected
from .windows_local_hermes_direct_agent import actual_model_turn

REPO = "baonguyenlgn-ship-it/honey-hermes-smoke-lab"
PREDECESSOR_RUN = 41216407415
PREDECESSOR_SHA = "4bcc1d85a25b7906fa370020cbcfa452ddeb6941"
PREDECESSOR_NAME = "Hermes isolated automatic next LAB coding after real Windows QA"
ISOLATED_BRANCH = "hermes-lab/e1-durable-evidence-20261101"
TASK_ID = "HERMES-E1-STOCK-GAP-DURABLE-01"
TASK_NAME = "stock_gap"
SOURCE_MIN, SOURCE_MAX = 40, 2048
MAX_REPAIRS = 2
TESTS = (
    (0, 5, 5), (5, 5, 0), (8, 5, -3), (" 2 ", "10", 8),
    (-2, -1, 1), (100, 0, -100), ("07", "7", 0), (-100, 50, 150),
    (42, 17, -25),
)
PROMPT = (
    "Write ONLY Python source, not Markdown or commentary, defining exactly "
    "one function stock_gap(available, minimum). Return the signed integer "
    "shortage int(minimum) - int(available); negative results are REQUIRED "
    "if available exceeds minimum. Use only int, local variables, return, "
    "and integer subtraction. No imports, comments, IO, tools or extra functions."
)

def qa_new_e1_task(source: str) -> bytes:
    if not isinstance(source, str):
        raise QaRejected("E1_SOURCE_NOT_TEXT")
    raw = source.encode("utf-8")
    if not (SOURCE_MIN <= len(raw) <= SOURCE_MAX) or any(x in source for x in ("\r", "\x00", "\ufeff")):
        raise QaRejected("E1_BYTES_INVALID")
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError):
        raise QaRejected("E1_PYTHON_SYNTAX_INVALID") from None
    if len(tree.body) != 1 or len(list(ast.walk(tree))) > 48:
        raise QaRejected("E1_AST_SCOPE_INVALID")
    fn = tree.body[0]
    if not isinstance(fn, ast.FunctionDef) or fn.name != TASK_NAME or fn.decorator_list or fn.returns is not None:
        raise QaRejected("E1_FUNCTION_SCOPE_INVALID")
    args = fn.args
    if (len(args.args) != 2 or [a.arg for a in args.args] != ["available", "minimum"]
            or args.vararg or args.kwarg or args.posonlyargs or args.kwonlyargs
            or args.defaults or args.kw_defaults or any(a.annotation is not None for a in args.args)):
        raise QaRejected("E1_SIGNATURE_INVALID")
    # Reuse already accepted safe AST grammar, not the previous exact AST equality.
    _body(fn.body, top=True)
    scope = {"__builtins__": {"int": int}}
    try:
        exec(compile(tree, "<fixed-safe-e1-stock-gap>", "exec"), scope)
        func = scope[TASK_NAME]
        for available, minimum, expected in TESTS:
            got = func(available, minimum)
            if type(got) is not int or got != expected:
                raise QaRejected("E1_BEHAVIOR_INVALID")
    except QaRejected:
        raise
    except Exception:
        raise QaRejected("E1_RUNTIME_INVALID") from None
    return raw

def prove_predecessor_and_queue() -> dict:
    url = f"https://api.github.com/repos/{REPO}/actions/runs/{PREDECESSOR_RUN}"
    request = urllib.request.Request(
        url, headers={"Accept": "application/vnd.github+json",
                      "User-Agent": "honey-hermes-E1-immutable-readback"},
        method="GET",
    )
    with urllib.request.urlopen(request, timeout=12) as response:
        if response.status != 200 or response.geturl() != url:
            raise RuntimeError("E1_PREDECESSOR_HTTP_UNTRUSTED")
        raw = response.read(65537)
    if len(raw) > 65536:
        raise RuntimeError("E1_PREDECESSOR_METADATA_OVERSIZE")
    p = json.loads(raw)
    if (p.get("id") != PREDECESSOR_RUN
            or p.get("name") != PREDECESSOR_NAME
            or p.get("head_sha") != PREDECESSOR_SHA
            or p.get("head_branch") != "hermes-lab/honey-isolated-gateway-diagnostics-20261031"
            or p.get("status") != "completed"
            or p.get("conclusion") != "success"
            or p.get("repository", {}).get("full_name") != REPO):
        raise RuntimeError("E1_PREDECESSOR_REAL_WINDOWS_PASS_NOT_PROVEN")
    # Read-only Owner mission discovery is distinct from execution consent.
    q = read_only_live_discovery()
    if (q.get("status") != "WAIT_NEW_OWNER_APPROVED_CURRENT_HEAD_MISSION"
            or q.get("execution_authority_granted") is not False
            or q.get("ledger_claimed") is not False
            or q.get("model_started") is not False):
        raise RuntimeError("E1_OWNER_QUEUE_NOT_SAFE_FOR_FIXED_LAB")
    return {"previous_run": PREDECESSOR_RUN, "owner_queue": q["status"]}

def main() -> None:
    if (os.environ.get("GITHUB_REPOSITORY") != REPO
            or os.environ.get("GITHUB_REF") != "refs/heads/" + ISOLATED_BRANCH
            or not os.environ.get("GITHUB_RUN_ID")
            or not os.environ.get("GITHUB_SHA")):
        raise RuntimeError("E1_WRONG_GITHUB_SCOPE")
    evidence = prove_predecessor_and_queue()
    upstream = Path(os.environ["HERMES_UPSTREAM_SOURCE"]).resolve()
    actual = subprocess.check_output(["git", "-C", str(upstream), "rev-parse", "HEAD"],
                                    text=True).strip()
    if actual != PINNED_HERMES:
        raise RuntimeError("E1_HERMES_UPSTREAM_SHA_MISMATCH")
    temp = Path(os.environ["RUNNER_TEMP"]).resolve() / "e1-new-real-agent-request"
    temp.mkdir(mode=0o700, exist_ok=False)
    artifact = Path(os.environ["RUNNER_TEMP"]).resolve() / "e1-produced-original"
    artifact.mkdir(mode=0o700, exist_ok=False)
    prompt = PROMPT
    for attempt in range(MAX_REPAIRS + 1):
        print("HERMES_E1_REAL_MODEL_ATTEMPT=" + str(attempt + 1), flush=True)
        model_output = actual_model_turn(prompt, attempt, upstream, temp)
        try:
            try:
                original_source, _ = strict_python_envelope(model_output)
            except ValueError:
                raise QaRejected("E1_UNTRUSTED_MODEL_ENVELOPE") from None
            source = qa_new_e1_task(original_source)
        except QaRejected as error:
            reason = str(error)
            print("HERMES_E1_INDEPENDENT_QA_REJECTED=" + reason, flush=True)
            if attempt == MAX_REPAIRS:
                raise RuntimeError("E1_REAL_MODEL_REPAIR_BUDGET_EXHAUSTED")
            prompt = (PROMPT + " Independent QA rejected previous reply: " + reason +
                      ". Fix it; output ONLY the exact Python function with return "
                      "int(minimum) - int(available).")
            continue
        digest = hashlib.sha256(source).hexdigest()
        # Unique run-specific artifact. Exact model original bytes are written
        # only after real QA PASS, never synthesized from EXPECTED.
        p = artifact / "original_model_generated.py"
        p.write_bytes(source)
        manifest = {
            "schema": "honey.hermes.real-model-durable-evidence.v1",
            "task_id": TASK_ID,
            "evidence_kind": "UNSIGNED_ISOLATED_LOOPBACK_TEST",
            "source_filename": p.name,
            "source_sha256": digest,
            "source_bytes": len(source),
            "source_branch": ISOLATED_BRANCH,
            "source_commit": os.environ["GITHUB_SHA"],
            "github_run_id": int(os.environ["GITHUB_RUN_ID"]),
            "predecessor_windows_run": evidence["previous_run"],
            "model_attempts": attempt + 1,
            "repairs": attempt,
            "model": "local-loopback-Qwen2.5-Coder-1.5B",
            "hermes_upstream_sha": PINNED_HERMES,
            "qa": "AST_ALLOWLIST_PLUS_BEHAVIOR",
            "independent_download_qa": "PENDING",
            "signed_gate_b": False,
            "production_authorized": False,
            "unattended_dispatch_proven": False,
        }
        (artifact / "manifest.json").write_text(
            json.dumps(manifest, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print("HERMES_E1_REAL_MODEL_QA_PASS_SOURCE_WRITTEN_TO_RUNNER_ARTIFACT=" + digest, flush=True)
        print("HERMES_E1_ARTIFACT_BYTES=" + str(len(source)), flush=True)
        # The fixed LAB task has no customer input or secrets. This accepted
        # code may be independently archived in an isolated GitHub evidence
        # commit AFTER artifact download QA; never print model credentials.
        print("HERMES_E1_ACCEPTED_SOURCE_BASE64=" + base64.b64encode(source).decode("ascii"), flush=True)
        print("HERMES_E1_INDEPENDENT_READBACK=PENDING", flush=True)
        return
    raise RuntimeError("E1_UNREACHABLE")

if __name__ == "__main__":
    main()
