import hashlib
import json
import unittest
from hermes_lab_local.codespaces_broker import validate

SOURCE=b"def normalize_label(text):\n    return str(text).strip().casefold()\n"
def good():
    return {"schema":"hermes.isolated.original-source.v1","run":"codespace-task-01",
        "hermes_sha":"bf0203a794a07aac3ff764972ab9087baa4e4f4e",
        "sha256":hashlib.sha256(SOURCE).hexdigest(),"size":len(SOURCE),
        "origin_cloud_authenticated":False,"core_authorized":False,
        "production":False,"human_qa":False}

class BrokerGateTests(unittest.TestCase):
    def test_only_pinned_lab_original_bytes_pass(self):
        x=validate(SOURCE,json.dumps(good()).encode())
        self.assertEqual(x["sha256"],hashlib.sha256(SOURCE).hexdigest())
        self.assertFalse(x["provider_origin_signed"])
        self.assertFalse(x["external_worker_identity_verified"])
        self.assertFalse(x["production_authorized"])
    def test_reject_changed_bytes(self):
        with self.assertRaises(ValueError):
            validate(SOURCE+b"# extra",json.dumps(good()).encode())
    def test_reject_forged_authority(self):
        for field in ("core_authorized","production","human_qa","origin_cloud_authenticated"):
            meta=good();meta[field]=True
            with self.subTest(field=field),self.assertRaises(ValueError):
                validate(SOURCE,json.dumps(meta).encode())
    def test_reject_false_source(self):
        x=good();x["hermes_sha"]="0"*40
        with self.assertRaises(ValueError): validate(SOURCE,json.dumps(x).encode())
    def test_reject_invalid_manifest(self):
        for body in (b"not json",b"[]"*2100,b"[]"):
            with self.assertRaises(ValueError): validate(SOURCE,body)
    def test_reject_tainted_source_that_has_valid_hash(self):
        tainted=b"def normalize_label(text):\n    return eval('42')\n"
        x=good();x["sha256"]=hashlib.sha256(tainted).hexdigest();x["size"]=len(tainted)
        with self.assertRaises(ValueError):validate(tainted,json.dumps(x).encode())
