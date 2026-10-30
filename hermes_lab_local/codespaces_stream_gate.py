"""Fail closed when a Hermes CLI stream-json response is not one successful original-source result.

Never print the raw stream, tool arguments, session credentials or diagnostics.
"""
import json
import sys
from pathlib import Path

LIMIT=65536

def terminal_source(stream: str)->str:
    if len(stream.encode("utf8")) > LIMIT:
        raise ValueError("STREAM_TOO_LARGE")
    lines=stream.splitlines()
    if not (2<=len(lines)<=512):
        raise ValueError("EVENT_COUNT_BOUNDS")
    events=[]
    for line in lines:
        x=json.loads(line)
        if not isinstance(x,dict) or not isinstance(x.get("type"),str):
            raise ValueError("NON_PROTOCOL_EVENT")
        events.append(x)
    if events[0].get("type")!="system" or events[0].get("subtype")!="init":
        raise ValueError("MISSING_PROTOCOL_INIT")
    terminals=[x for x in events if x.get("type")=="result"]
    if len(terminals)!=1 or events[-1] is not terminals[0]:
        raise ValueError("TERMINAL_NOT_UNIQUE_OR_LAST")
    if any(x.get("type") in ("tool_use","tool_result") for x in events):
        raise ValueError("TOOLS_NOT_PERMITTED_IN_FIRST_SMOKE")
    x=terminals[0]
    if x.get("exit_code")!=0 or x.get("error") or x.get("replay_gap"):
        raise ValueError("HERMES_TURN_NOT_CONFIRMED")
    text=x.get("text")
    if not isinstance(text,str) or not text.strip():
        raise ValueError("EMPTY_OR_INVALID_ORIGINAL_RESPONSE")
    if len(text.encode("utf8"))>2048:
        raise ValueError("RESPONSE_TOO_LARGE")
    return text

if __name__=="__main__":
    if len(sys.argv)!=3:
        raise SystemExit("usage: codespaces_stream_gate.py original-events.jsonl private-output.txt")
    out=terminal_source(Path(sys.argv[1]).read_text(encoding="utf8"))
    dst=Path(sys.argv[2])
    with dst.open("x", encoding="utf8") as f:
        f.write(out)
    print("HERMES_ORIGINAL_STREAM_VERIFIED bytes="+str(len(out.encode("utf8"))))
