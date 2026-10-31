"""Focused NEW QA for response envelopes at failing Hermes next-task gate D.

No model, GitHub writes, signer, legacy A/C PASS rerun, or external service.
"""
import unittest

from hermes_lab_local.strict_model_code_envelope import strict_python_envelope
from hermes_lab_local.windows_hermes_next_lab_task import qa_new_task
from hermes_lab_local.windows_local_hermes_coding import QaRejected

SOURCE = "def is_low_stock(available, minimum):\n    return int(available) < int(minimum)"
VALID = (
    (SOURCE, "RAW_MODEL_PYTHON"),
    ("\n" + SOURCE + "\n", "RAW_MODEL_PYTHON"),
    ("\x60\x60\x60python\n" + SOURCE + "\n\x60\x60\x60", "SINGLE_FULL_PYTHON_FENCE"),
    ("\x60\x60\x60py\n" + SOURCE + "\n\x60\x60\x60", "SINGLE_FULL_PYTHON_FENCE"),
)
UNSAFE = (
    "Here is your code:\n\x60\x60\x60python\n" + SOURCE + "\n\x60\x60\x60",
    "\x60\x60\x60python\n" + SOURCE + "\n\x60\x60\x60\nPlease run it.",
    "\x60\x60\x60python\n" + SOURCE + "\n\x60\x60\x60\n\x60\x60\x60python\n" + SOURCE + "\n\x60\x60\x60",
    "\x60\x60\x60python\n" + SOURCE,
    "\x60\x60\x60bash\n" + SOURCE + "\n\x60\x60\x60",
    "\ufeff" + SOURCE,
    SOURCE.replace("\n", "\r\n"),
    SOURCE + "\x00",
    " " * 2049,
    "\x60\x60\x60python\nimport os\n" + SOURCE + "\n\x60\x60\x60",
)

class NextTaskEnvelopeAcceptance(unittest.TestCase):
    def test_valid_raw_and_single_full_fence_round_trip(self):
        for source, marker in VALID:
            with self.subTest(marker=marker):
                candidate, actual = strict_python_envelope(source)
                self.assertEqual(actual, marker)
                approved = qa_new_task(candidate)
                self.assertEqual(approved.strip(), SOURCE.encode("utf-8"))

    def test_malformed_envelopes_never_become_executable_code(self):
        for source in UNSAFE:
            with self.subTest(source_prefix=source[:12]):
                try:
                    candidate, _ = strict_python_envelope(source)
                except ValueError:
                    continue
                with self.assertRaises(QaRejected):
                    qa_new_task(candidate)

    def test_never_reconstruct_missing_python(self):
        candidate, marker = strict_python_envelope(
            "\x60\x60\x60python\ndef is_low_stock(x):\n    pass\n\x60\x60\x60")
        self.assertEqual(marker, "SINGLE_FULL_PYTHON_FENCE")
        with self.assertRaises(QaRejected):
            qa_new_task(candidate)

    def test_envelope_rejection_is_not_a_model_pass(self):
        with self.assertRaises(ValueError):
            strict_python_envelope(
                "I generated the function.\n\x60\x60\x60python\n" + SOURCE + "\n\x60\x60\x60")

if __name__ == "__main__":
    unittest.main()
