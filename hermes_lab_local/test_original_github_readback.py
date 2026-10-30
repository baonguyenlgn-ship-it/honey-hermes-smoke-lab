"""Independent GitHub readback for one accepted Hermes LAB source artifact.

No provider access, no privileged worker/owner claims and no arbitrary generated code
execution before SHA and exact-AST verification. Checks GitHub bytes, not Nous Cloud signed origin.
"""
import ast
import hashlib
import json
from pathlib import Path
import unittest
import subprocess

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT / "hermes_lab_local/generated/normalize_label.py"
PROVENANCE=ROOT / "hermes_lab_local/generated/provenance.json"
EXPECTED_SHA="e05b4f379ed8382cfc1662dcd791ac607c3befdfec8b8aea8c3cc16f6592cdc0"
EXPECTED_HERMES="bf0203a794a07aac3ff764972ab9087baa4e4f4e"
CANONICAL="def normalize_label(text):\n    return str(text).strip().casefold()"

class GithubOriginalReadback(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if SOURCE.is_symlink() or PROVENANCE.is_symlink():
            raise AssertionError("SYMLINK_ARTIFACT_REJECTED")
        # Windows checkout can normalize LF to CRLF; attest immutable Git blob bytes, not worktree text.
        source=subprocess.check_output(("git","show","HEAD:hermes_lab_local/generated/normalize_label.py"),cwd=ROOT)
        cls.provenance=json.loads(PROVENANCE.read_text(encoding="utf-8"))
        assert len(source)==66, "SOURCE_LEN_CHANGED"
        assert hashlib.sha256(source).hexdigest()==EXPECTED_SHA, "SOURCE_SHA_CHANGED"
        p=cls.provenance
        assert set(p)=={
            "core_guard_authorized","external_worker_identity_verified",
            "merge_authorized","production_authorized","provider_origin_signed",
            "schema","sha256","size","upstream_hermes_sha",
        }, "RECEIPT_FIELDS_CHANGED"
        assert p["schema"]=="honey.hermes.codespaces.original-local-claim.v1"
        assert p["sha256"]==EXPECTED_SHA and p["size"]==len(source)
        assert p["upstream_hermes_sha"]==EXPECTED_HERMES
        assert all(p[k] is False for k in (
            "core_guard_authorized","external_worker_identity_verified",
            "merge_authorized","production_authorized","provider_origin_signed"
        )), "FALSE_AUTHORITY_CLAIMS"
        tree=ast.parse(source.decode("utf-8"))
        assert ast.dump(tree,include_attributes=False)==ast.dump(
            ast.parse(CANONICAL),include_attributes=False
        ), "UNEXPECTED_CODE_AST"
        scope={}
        exec(compile(tree, "<strictly-pinned-original>", "exec"),scope)
        cls.normalize=staticmethod(scope["normalize_label"])

    def test_vietnamese_mango(self):
        self.assertEqual(self.normalize("  Xoài Cát Chu  "),"xoài cát chu")
    def test_vietnamese_pomelo(self):
        self.assertEqual(self.normalize("  BƯỞI  "),"bưởi")
    def test_english(self):
        self.assertEqual(self.normalize("  Coconut  "),"coconut")
    def test_korean(self):
        self.assertEqual(self.normalize("  안녕하세요  "),"안녕하세요")
    def test_chinese(self):
        self.assertEqual(self.normalize("  芒果  "),"芒果")
    def test_basic_ascii(self):
        self.assertEqual(self.normalize("  MANGO  "),"mango")
    def test_empty(self):
        self.assertEqual(self.normalize(""),"")
    def test_spaces_only(self):
        self.assertEqual(self.normalize("  " ),"")
    def test_number(self):
        self.assertEqual(self.normalize(123),"123")
    def test_casefold_german(self):
        self.assertEqual(self.normalize("Straße"),"strasse")
    def test_unicode_dotted_i(self):
        self.assertEqual(self.normalize("İ"),"i\u0307")
    def test_none(self):
        self.assertEqual(self.normalize(None),"none")

if __name__=="__main__":
    unittest.main(verbosity=2)
