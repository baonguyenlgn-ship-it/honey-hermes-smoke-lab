import json
import unittest
from hermes_lab_local.codespaces_stream_gate import terminal_source

def stream(reply="def normalize_label(text):\n    return str(text).strip().casefold()\n", exit=0):
    events=[{"type":"system","subtype":"init","model":"nous"},
            {"type":"text","text":reply},
            {"type":"result","exit_code":exit,"text":reply,"session_id":"local-test"}]
    return "\n".join(json.dumps(x) for x in events)+"\n"

class FailClosedProtocolTests(unittest.TestCase):
    def test_clean_stream(self):
        self.assertIn("casefold()",terminal_source(stream()))
    def test_reject_unsuccessful_turn(self):
        with self.assertRaises(ValueError):
            terminal_source(stream(exit=1))
    def test_reject_duplicate_terminal(self):
        s=stream()
        result=json.dumps({"type":"result","exit_code":0,"text":"duplicate"})
        with self.assertRaises(ValueError):
            terminal_source(s+result+"\n")
    def test_reject_tool_use(self):
        s=stream()
        events=s.splitlines()
        events.insert(1,json.dumps({"type":"tool_use","name":"terminal","input":{"cmd":"example"}}))
        with self.assertRaises(ValueError):
            terminal_source("\n".join(events))
    def test_reject_missing_init(self):
        with self.assertRaises(ValueError):
            terminal_source("\n".join(stream().splitlines()[1:]))
    def test_reject_no_real_source(self):
        with self.assertRaises(ValueError):
            terminal_source(stream(reply=""))
    def test_reject_replay_gap(self):
        events=[json.loads(x) for x in stream().splitlines()]
        events[-1]["replay_gap"]=True
        with self.assertRaises(ValueError):
            terminal_source("\n".join(json.dumps(x) for x in events))
    def test_reject_oversized_stream(self):
        with self.assertRaises(ValueError):
            terminal_source(stream("x"*66000))
    def test_reject_malformed_event(self):
        with self.assertRaises(json.JSONDecodeError):
            terminal_source("not-json\n"+stream())
    def test_reject_result_not_last(self):
        with self.assertRaises(ValueError):
            terminal_source(stream()+json.dumps({"type":"text","text":"later"})+"\n")
