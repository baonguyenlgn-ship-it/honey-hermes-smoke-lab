"""Fail-closed *bounded* semantic QA for the one fixed Hermes is_low_stock LAB task.

No arbitrary Python execution: source first passes a strict AST allowlist,
then deterministic behavioral tests. This is a separate, nonproduction test
task and does not authorize arbitrary GitHub work or provider execution.
"""
from __future__ import annotations

import ast
import re
from .windows_local_hermes_coding import QaRejected

MAX_BYTES = 2048
MAX_NODES = 55
_ARG_NAMES = ("available", "minimum")
_IDENT = re.compile(r"^[a-z][a-z0-9_]{0,31}$")
_TESTS = (
    (0, 1, True), (1, 0, False), (5, 5, False),
    (3, 5, True), (-1, 0, True), (" 2 ", "4", True),
    (10, 7, False), ("00", "+1", True), ("07", "7", False),
    (-100, -10, True), (100, -100, False),
)

def _reject(reason: str):
    raise QaRejected(reason)

def _name(name):
    if not isinstance(name, str) or not _IDENT.fullmatch(name) or "__" in name:
        _reject("DISALLOWED_VARIABLE")

def _expression(node):
    if isinstance(node, ast.Name):
        _name(node.id)
        if not isinstance(node.ctx, ast.Load):
            _reject("DISALLOWED_EXPRESSION")
        return
    if isinstance(node, ast.Constant):
        if type(node.value) not in (bool, int, str):
            _reject("DISALLOWED_CONSTANT")
        if type(node.value) is str and len(node.value) > 64:
            _reject("DISALLOWED_CONSTANT")
        if type(node.value) is int and abs(node.value) > 1000000:
            _reject("DISALLOWED_CONSTANT")
        return
    if isinstance(node, ast.Call):
        if (not isinstance(node.func, ast.Name) or node.func.id != "int"
                or len(node.args) != 1 or node.keywords):
            _reject("DISALLOWED_CALL")
        _expression(node.args[0])
        return
    if isinstance(node, ast.Compare):
        if (not node.ops or len(node.ops) != 1 or len(node.comparators) != 1
                or not isinstance(node.ops[0], (ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.Eq, ast.NotEq))):
            _reject("DISALLOWED_COMPARISON")
        _expression(node.left)
        _expression(node.comparators[0])
        return
    if isinstance(node, ast.BoolOp):
        if not isinstance(node.op, (ast.And, ast.Or)) or len(node.values) > 3:
            _reject("DISALLOWED_BOOLOP")
        for item in node.values:
            _expression(item)
        return
    if isinstance(node, ast.UnaryOp):
        if not isinstance(node.op, ast.Not):
            _reject("DISALLOWED_UNARY")
        _expression(node.operand)
        return
    if isinstance(node, ast.IfExp):
        _expression(node.test)
        _expression(node.body)
        _expression(node.orelse)
        return
    if isinstance(node, ast.BinOp):
        if not isinstance(node.op, (ast.Add, ast.Sub)):
            _reject("DISALLOWED_BINARY")
        _expression(node.left)
        _expression(node.right)
        return
    _reject("DISALLOWED_EXPRESSION")

def _body(nodes, *, top=False):
    if not nodes or len(nodes) > 6:
        _reject("DISALLOWED_STATEMENT_COUNT")
    for idx, statement in enumerate(nodes):
        if (top and idx == 0 and isinstance(statement, ast.Expr)
                and isinstance(statement.value, ast.Constant)
                and type(statement.value.value) is str
                and len(statement.value.value) <= 120):
            continue
        if isinstance(statement, ast.Assign):
            if len(statement.targets) != 1 or not isinstance(statement.targets[0], ast.Name):
                _reject("DISALLOWED_ASSIGN_TARGET")
            _name(statement.targets[0].id)
            if statement.targets[0].id in ("int",):
                _reject("BUILTIN_SHADOWING_DENIED")
            _expression(statement.value)
        elif isinstance(statement, ast.Return):
            if statement.value is None:
                _reject("EMPTY_RETURN_DENIED")
            _expression(statement.value)
        elif isinstance(statement, ast.If):
            _expression(statement.test)
            _body(statement.body)
            if statement.orelse:
                _body(statement.orelse)
        else:
            _reject("DISALLOWED_STATEMENT")

def qa_semantic_low_stock(source: str) -> bytes:
    if not isinstance(source, str):
        _reject("NON_TEXT_SOURCE")
    raw=source.encode("utf-8")
    if not (35 <= len(raw) <= MAX_BYTES) or any(ch in source for ch in ("\x00", "\r", "\ufeff")):
        _reject("SOURCE_BYTES_INVALID")
    try:
        tree=ast.parse(source)
    except (ValueError, SyntaxError):
        _reject("PYTHON_SYNTAX_INVALID")
    if len(list(ast.walk(tree))) > MAX_NODES or len(tree.body) != 1:
        _reject("SOURCE_STRUCTURE_EXCEEDS_SCOPE")
    fn=tree.body[0]
    if not isinstance(fn, (ast.FunctionDef,)) or fn.name != "is_low_stock":
        _reject("ONE_EXACT_FUNCTION_REQUIRED")
    args=fn.args
    if (len(args.args) != 2 or [arg.arg for arg in args.args] != list(_ARG_NAMES)
            or any(arg.annotation is not None for arg in args.args)
            or args.posonlyargs or args.kwonlyargs or args.vararg or args.kwarg
            or args.defaults or args.kw_defaults
            or fn.decorator_list or fn.returns is not None
            or getattr(fn, "type_params", None)):
        _reject("FUNCTION_SIGNATURE_MISMATCH")
    _body(fn.body, top=True)
    # After strict AST validation, only pure/finite expressions are possible.
    # Never grant access to Python builtins beyond int; no disk/network.
    isolated={"__builtins__":{"int":int}}
    try:
        exec(compile(tree,"<bounded-hermes-low-stock-test>","exec"), isolated)
        fn=isolated["is_low_stock"]
        for available, minimum, expected in _TESTS:
            if fn(available, minimum) is not expected:
                _reject("BEHAVIOR_MISMATCH")
    except QaRejected:
        raise
    except Exception:
        _reject("BEHAVIOR_RUNTIME_INVALID")
    return raw
