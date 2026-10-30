"""Parse a bounded Hermes LOCAL model response. Does not validate cloud provenance."""
import ast
import hashlib
import json
import sys
from pathlib import Path

def gate(response):
    text = response.strip()
    if not text.startswith("def normalize_label(text):") or len(text.encode()) > 2048:
        raise ValueError("RESPONSE_BOUNDARY")
    tree = ast.parse(text)
    if len(tree.body) != 1 or not isinstance(tree.body[0], ast.FunctionDef):
        raise ValueError("SINGLE_FUNCTION_ONLY")
    for item in ast.walk(tree):
        if isinstance(item, (ast.Import, ast.ImportFrom, ast.Lambda, ast.With, ast.While, ast.For, ast.Try, ast.ClassDef)):
            raise ValueError("DISALLOWED_SYNTAX")
        if isinstance(item, ast.Call):
            method = item.func.id if isinstance(item.func, ast.Name) else getattr(item.func, "attr", "")
            if method not in ("str", "strip", "casefold"):
                raise ValueError("UNSAFE_CALL")
    if ".strip()" not in text or ".casefold()" not in text:
        raise ValueError("EXPECTED_NORMALIZATION_MISSING")
    return (text + "\n").encode()

if __name__ == "__main__":
    if len(sys.argv) != 5:
        raise SystemExit("usage: parser raw-output output-dir workflow-id hermes-git-sha")
    raw, dest, run, hermes_sha = sys.argv[1:]
    source = gate(Path(raw).read_text(encoding="utf8"))
    target = Path(dest)
    target.mkdir(parents=True, exist_ok=False)
    (target / "normalize_label.py").write_bytes(source)
    manifest = {"schema": "hermes.local.cpu.smoke.v1", "run": run,
                "hermes_sha": hermes_sha, "sha256": hashlib.sha256(source).hexdigest(),
                "size": len(source), "origin_cloud_authenticated": False,
                "human_qa": False, "core_authorized": False, "production": False}
    (target / "manifest.json").write_text(json.dumps(manifest) + "\n")
    print("HERMES_LOCAL_BOUNDARY_PASS sha256=" + manifest["sha256"])
