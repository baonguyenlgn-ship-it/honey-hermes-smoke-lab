"""Only executes when an actual trusted broker publishes repair_generated files.
Independent Windows QA reads immutable git blob bytes, not CRLF-normalized files.
"""
import hashlib,json,subprocess,unittest
from pathlib import Path
from hermes_lab_local.repair_loop import qa,QaFailure,MODEL,HERMES_SHA,TASK

ROOT=Path(__file__).resolve().parents[1]
SOURCE="hermes_lab_local/repair_generated/normalize_label.py"
RECEIPT="hermes_lab_local/repair_generated/receipt.json"

class RealGitBlobReadback(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source=subprocess.check_output(("git","show","HEAD:"+SOURCE),cwd=ROOT)
        receipt_bytes=subprocess.check_output(("git","show","HEAD:"+RECEIPT),cwd=ROOT)
        r=json.loads(receipt_bytes)
        expected={"schema","task_id","model","sha256","size","attempts","repairs",
                  "hermes_sha","provider_origin_signed","core_guard_authorized",
                  "production_authorized","unattended_execution_authorized"}
        assert set(r)==expected and r["schema"]=="honey.hermes.lab-repair-readback.v1"
        assert r["task_id"]==TASK and r["model"]==MODEL and r["hermes_sha"]==HERMES_SHA
        assert all(r[k] is False for k in ("provider_origin_signed","core_guard_authorized",
                   "production_authorized","unattended_execution_authorized"))
        assert type(r["attempts"]) is int and 1<=r["attempts"]<=3
        assert type(r["repairs"]) is int and r["repairs"]==r["attempts"]-1
        assert len(source)==r["size"] and hashlib.sha256(source).hexdigest()==r["sha256"]
        assert qa(source.decode("utf8"))==source
        cls.proof=r
    def test_original_byte_hash(self):
        self.assertEqual(len(self.proof["sha256"]),64)
    def test_no_core_admission(self):
        self.assertIs(self.proof["core_guard_authorized"],False)
    def test_no_prod(self):
        self.assertIs(self.proof["production_authorized"],False)
    def test_no_unattended_execution(self):
        self.assertIs(self.proof["unattended_execution_authorized"],False)
    def test_bounded_repairs(self):
        self.assertLessEqual(self.proof["repairs"],2)
    def test_no_signed_origin_claim(self):
        self.assertIs(self.proof["provider_origin_signed"],False)
