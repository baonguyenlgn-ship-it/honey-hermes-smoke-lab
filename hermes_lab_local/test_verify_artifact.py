import unittest
from hermes_lab_local.verify_artifact import gate

class LocalArtifactGateTests(unittest.TestCase):
    def test_accept_minimal_safe_function(self):
        x=gate("def normalize_label(text):\n    return str(text).strip().casefold()\n")
        self.assertIn(b"casefold()",x)

    def test_reject_unsafe_calls(self):
        bad=[
            "def normalize_label(text):\n    import os\n    return text.strip().casefold()",
            "def normalize_label(text):\n    return eval('1').strip().casefold()",
            "def normalize_label(text):\n    return text.strip()",
            "print('x')",
        ]
        for s in bad:
            with self.subTest(text=s):
                with self.assertRaises((ValueError,SyntaxError)):
                    gate(s)
