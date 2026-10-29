#!/usr/bin/env python3
"""Idempotent lab task runner with a stdlib SQLite idempotency ledger.

CLI: python3 lab_task_runner.py --db PATH < payload.json
Input keys: task_id (non-empty string), text (string), max_length (positive int).
Success JSON is {task_id, status: completed|duplicate, output}; errors are JSON.
Repeated identical payloads return the stored output; a changed payload under the
same task ID is rejected. Writes are transactional, so an interrupted transaction
is rolled back by SQLite.
"""
import argparse
import hashlib
import json
import sqlite3
import sys

EXIT_OK = 0
EXIT_INVALID = 1
EXIT_USAGE = 2
EXIT_CONFLICT = 3
EXIT_INTERNAL = 4
REQUIRED_KEYS = frozenset({"task_id", "text", "max_length"})
_LEDGER_DDL = (
    "CREATE TABLE IF NOT EXISTS task_ledger ("
    " task_id TEXT PRIMARY KEY,"
    " payload_digest TEXT NOT NULL,"
    " output TEXT NOT NULL,"
    " created_at TEXT NOT NULL DEFAULT (datetime('now'))"
    ")"
)

class TaskError(Exception):
    def __init__(self, code, message, exit_code, **details):
        super().__init__(message)
        self.code = code
        self.message = message
        self.exit_code = exit_code
        self.details = details

def _payload_digest(text, max_length):
    canonical = json.dumps([text, max_length], separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

def _normalize(text, max_length):
    return " ".join(text.split())[:max_length].rstrip(" ")

def validate_payload(obj):
    issues = []
    if not isinstance(obj, dict):
        raise TaskError("invalid_payload", "payload must be a JSON object", EXIT_INVALID)
    missing = REQUIRED_KEYS - obj.keys()
    unexpected = obj.keys() - REQUIRED_KEYS
    if missing:
        issues.append("missing key(s): " + ", ".join(sorted(missing)))
    if unexpected:
        issues.append("unexpected key(s): " + ", ".join(sorted(unexpected)))
    if "task_id" in obj:
        if not isinstance(obj["task_id"], str):
            issues.append("task_id must be a string")
        elif not obj["task_id"]:
            issues.append("task_id must be a non-empty string")
    if "text" in obj and not isinstance(obj["text"], str):
        issues.append("text must be a string")
    if "max_length" in obj:
        max_length = obj["max_length"]
        if isinstance(max_length, bool) or not isinstance(max_length, int):
            issues.append("max_length must be an int (bool is rejected)")
        elif max_length < 1:
            issues.append("max_length must be a positive int")
    if issues:
        raise TaskError("invalid_payload", "; ".join(issues), EXIT_INVALID, issues=issues)
    return obj["task_id"], obj["text"], obj["max_length"]

def _commit(conn):
    conn.commit()

def run_task(db_path, task_id, text, max_length):
    digest = _payload_digest(text, max_length)
    output = _normalize(text, max_length)
    conn = sqlite3.connect(db_path, timeout=30.0, isolation_level=None)
    try:
        conn.execute("BEGIN IMMEDIATE")
        try:
            conn.execute(_LEDGER_DDL)
            row = conn.execute(
                "SELECT payload_digest, output FROM task_ledger WHERE task_id = ?",
                (task_id,),
            ).fetchone()
            if row is None:
                conn.execute(
                    "INSERT INTO task_ledger (task_id, payload_digest, output) VALUES (?, ?, ?)",
                    (task_id, digest, output),
                )
                _commit(conn)
                return {"task_id": task_id, "status": "completed", "output": output}
            stored_digest, stored_output = row
            if stored_digest == digest:
                conn.rollback()
                return {"task_id": task_id, "status": "duplicate", "output": stored_output}
            conn.rollback()
            raise TaskError(
                "payload_mismatch",
                "task_id is already recorded with a different payload; the ledger entry was not overwritten",
                EXIT_CONFLICT,
                stored_digest=stored_digest,
                received_digest=digest,
            )
        except BaseException:
            try:
                conn.rollback()
            except sqlite3.Error:
                pass
            raise
    finally:
        conn.close()

class _JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        raise TaskError("usage_error", message, EXIT_USAGE)

def _emit(payload):
    sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
    sys.stdout.flush()

def main(argv=None):
    task_id = None
    try:
        parser = _JsonArgumentParser(
            prog="lab_task_runner.py",
            description="Idempotent lab task runner with an SQLite idempotency ledger.",
        )
        parser.add_argument("--db", required=True, metavar="PATH", help="path to the SQLite ledger file (required)")
        args = parser.parse_args(argv)
        raw = sys.stdin.read()
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise TaskError(
                "invalid_json",
                "stdin is not valid JSON: %s (line %d, column %d)" % (exc.msg, exc.lineno, exc.colno),
                EXIT_INVALID,
            ) from None
        if isinstance(obj, dict) and isinstance(obj.get("task_id"), str):
            task_id = obj["task_id"]
        task_id, text, max_length = validate_payload(obj)
        _emit(run_task(args.db, task_id, text, max_length))
        return EXIT_OK
    except TaskError as err:
        _emit({"task_id": task_id if isinstance(task_id, str) else None, "status": "error",
               "error": {"code": err.code, "message": err.message, **err.details}})
        return err.exit_code
    except Exception as exc:
        _emit({"task_id": None, "status": "error", "error": {
            "code": "internal_error", "message": "%s: %s" % (type(exc).__name__, exc)}})
        return EXIT_INTERNAL

if __name__ == "__main__":
    sys.exit(main())
