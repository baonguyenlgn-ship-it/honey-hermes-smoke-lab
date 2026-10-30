"""Fixtures simulate candidate answers. PASS here is NOT real Hermes inference."""
import json,hashlib,unittest
from tempfile import TemporaryDirectory
from pathlib import Path
from hermes_lab_local.repair_loop import EXPECTED,qa,run_loop,receipt,ProviderError,QaFailure,prompt
from hermes_lab_local.repair_broker import validate
GOOD=EXPECTED
BAD="def normalize_label(text):\n    return str(text).strip()"
def accepted_receipt(attempts=1):
    sha=hashlib.sha256(GOOD.encode()).hexdigest()
    return {"schema":"honey.hermes.bounded-repair-lab.v1","task_id":"hermes-lab-rename-label-v1",
            "model":"upstage/solar-mini4:free","hermes_sha":"bf0203a794a07aac3ff764972ab9087baa4e4f4e",
            "status":"QA_PASS","attempts":attempts,"repairs":attempts-1,
            "qa_events":[{"attempt":i+1,"status":"QA_REJECTED" if i<attempts-1 else "QA_PASS",
                          "detail":"UNSAFE_AST" if i<attempts-1 else sha} for i in range(attempts)],
            "provider_origin_signed":False,"core_guard_authorized":False,
            "production_authorized":False,"merge_authorized":False,
            "automatic_unattended_mode":False,"sha256":sha,"size":len(GOOD.encode())}

class RepairStateFixtureQA(unittest.TestCase):
    def test_no_repair(self):
        calls=[];a,b=run_loop(lambda p,i:calls.append(i) or GOOD)
        self.assertEqual((a["status"],a["repairs"],calls),("QA_PASS",0,[0]))
        self.assertEqual(b,GOOD.encode())
    def test_one_real_state_transition(self):
        calls=[];events=[]
        def f(p,i):calls.append(i);return BAD if i==0 else GOOD
        a,b=run_loop(f,events)
        self.assertEqual((a["attempts"],calls),(2,[0,1]))
        self.assertEqual([e["status"] for e in events],["QA_REJECTED","QA_PASS"])
    def test_two_state_transitions(self):
        calls=[];a,b=run_loop(lambda p,i:calls.append(i) or (BAD if i<2 else GOOD))
        self.assertEqual((a["repairs"],calls),(2,[0,1,2]))
    def test_exhausted_never_attempt_four(self):
        calls=[];a,b=run_loop(lambda p,i:calls.append(i) or BAD)
        self.assertEqual((a["status"],calls),("QA_EXHAUSTED",[0,1,2]))
        self.assertIsNone(b)
    def test_provider_failure_never_retried(self):
        calls=[]
        def f(p,i):calls.append(i);raise ProviderError("FAILED")
        with self.assertRaises(ProviderError):run_loop(f)
        self.assertEqual(calls,[0])
    def test_no_unsafe_code(self):
        cases=[BAD,"def normalize_label(text):\n import os\n return text",
               "def normalize_label(text):\n return eval('1')",GOOD+"\n#comment",
               GOOD+"\r",GOOD+"\nprint('x')",""]
        for c in cases:
            with self.subTest(c=c[:30]),self.assertRaises(QaFailure):qa(c)
    def test_unicode_safe_function(self):self.assertEqual(qa(GOOD),GOOD.encode())
    def test_feedback_bounded(self):
        self.assertIn("UNSAFE_AST",prompt(1,"UNSAFE_AST"))
        self.assertNotIn("ghp_",prompt(1,"UNSAFE_AST"))
    def test_private_receipt_denies_authority(self):
        with TemporaryDirectory() as tmp:
            from hermes_lab_local import repair_loop
            old=repair_loop.OUTPUT
            try:
                repair_loop.OUTPUT=Path(tmp)
                j=[];r,b=run_loop(lambda p,i:GOOD,j)
                receipt(r,b,j)
                p=json.loads((Path(tmp)/"receipt.json").read_text())
                self.assertFalse(p["provider_origin_signed"])
                self.assertFalse(p["production_authorized"])
                self.assertFalse(p["automatic_unattended_mode"])
            finally:repair_loop.OUTPUT=old

class BrokerAdversarialQA(unittest.TestCase):
    def test_accept_one_to_three_provenance(self):
        for n in range(1,4):self.assertEqual(validate(GOOD.encode(),json.dumps(accepted_receipt(n)).encode())["attempts"],n)
    def test_reject_fourth_attempt(self):
        x=accepted_receipt(4)
        with self.assertRaises(ValueError):validate(GOOD.encode(),json.dumps(x).encode())
    def test_reject_authority_forgery(self):
        for field in ("provider_origin_signed","core_guard_authorized","production_authorized","automatic_unattended_mode"):
            x=accepted_receipt();x[field]=True
            with self.subTest(field=field),self.assertRaises(ValueError):validate(GOOD.encode(),json.dumps(x).encode())
    def test_reject_sha_tamper(self):
        x=accepted_receipt();x["sha256"]="0"*64
        with self.assertRaises(ValueError):validate(GOOD.encode(),json.dumps(x).encode())
    def test_reject_fake_history(self):
        x=accepted_receipt(2);x["qa_events"][0]["status"]="QA_PASS"
        with self.assertRaises(ValueError):validate(GOOD.encode(),json.dumps(x).encode())
    def test_reject_wrong_model(self):
        x=accepted_receipt();x["model"]="paid-provider"
        with self.assertRaises(ValueError):validate(GOOD.encode(),json.dumps(x).encode())
    def test_reject_changed_source_even_rehashed(self):
        b=b"def normalize_label(text):\n    return eval('1')"
        x=accepted_receipt();x["sha256"]=hashlib.sha256(b).hexdigest();x["size"]=len(b)
        x["qa_events"][0]["detail"]=x["sha256"]
        with self.assertRaises(ValueError):validate(b,json.dumps(x).encode())
    def test_reject_additional_fields(self):
        x=accepted_receipt();x["can_merge"]=True
        with self.assertRaises(ValueError):validate(GOOD.encode(),json.dumps(x).encode())
