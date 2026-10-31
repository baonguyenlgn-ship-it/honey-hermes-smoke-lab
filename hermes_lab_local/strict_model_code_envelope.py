"""Conservative source-envelope extraction for real local model output.

Never repair/construct model-authored code and never interpret arbitrary
natural-language prose as source. The only accepted representations are
raw Python or one complete, single fenced Python block (no surrounding text).
QA MUST subsequently validate the extracted code's exact AST + behavior.
"""
from __future__ import annotations

import re

MAX = 2048
FENCE = re.compile(r"\A[ \t]*```(?:python|py)?[ \t]*\n([^\r\x00﻿]*?)\n?```[ \t]*\n?\Z", re.I | re.S)

def strict_python_envelope(text: str) -> tuple[str, str]:
    if not isinstance(text, str):
        raise ValueError("INVALID_SOURCE_TYPE")
    raw=text.encode("utf-8")
    if len(raw)>MAX or b"\x00" in raw or b"\r" in raw or b"\xef\xbb\xbf" in raw:
        raise ValueError("INVALID_OR_OVERSIZE_SOURCE")
    if text.lstrip().startswith("```"):
        matched=FENCE.fullmatch(text)
        if matched is None or "```" in matched.group(1):
            raise ValueError("UNTRUSTED_CODE_ENVELOPE")
        return matched.group(1), "SINGLE_FULL_PYTHON_FENCE"
    # A partial code fence inside prose is not source, and cannot be stripped.
    if "```" in text:
        raise ValueError("UNTRUSTED_CODE_ENVELOPE")
    return text, "RAW_MODEL_PYTHON"
