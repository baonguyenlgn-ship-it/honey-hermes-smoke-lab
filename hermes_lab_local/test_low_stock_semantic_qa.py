"""NEW D-only adversarial, no-model semantic QA. No old PASS reruns."""
import unittest
from hermes_lab_local.low_stock_semantic_qa import qa_semantic_low_stock
from hermes_lab_local.windows_local_hermes_coding import QaRejected

VALID = [
    "def is_low_stock(available, minimum):\n    return int(available) < int(minimum)",
    "def is_low_stock(available, minimum):\n    available = int(available)\n    minimum = int(minimum)\n    return available < minimum",
    "def is_low_stock(available, minimum):\n    return True if int(available) < int(minimum) else False",
    "def is_low_stock(available, minimum):\n    if int(available) < int(minimum):\n        return True\n    else:\n        return False",
    'def is_low_stock(available, minimum):\n    """Check strictly below reorder point."""\n    return int(available) < int(minimum)',
]
BAD = [
    "import os\ndef is_low_stock(available, minimum):\n    return True",
    "def is_low_stock(available, minimum):\n    import os\n    return True",
    "def is_low_stock(available, minimum):\n    return __import__('os').getcwd()",
    "def is_low_stock(available, minimum):\n    return eval('True')",
    "def is_low_stock(available, minimum):\n    return int(available) <= int(minimum)",
    "def is_low_stock(available, minimum):\n    return int(available) > int(minimum)",
    "def is_low_stock(available, minimum):\n    return available < minimum",
    "def is_low_stock(available, minimum):\n    while True:\n        pass",
    "def is_low_stock(available, minimum):\n    return [x for x in range(10)]",
    "def is_low_stock(available, minimum):\n    return minimum.__class__",
    "def is_low_stock(available, minimum):\n    return is_low_stock(available, minimum)",
    "def is_low_stock(available, minimum):\n    global x\n    return True",
    "def is_low_stock(available, minimum):\n    return open('file')",
    "def is_low_stock(available, minimum):\n    return 1 ** 1000000",
    "def is_low_stock(available, minimum):\n    int = str\n    return True",
    "def is_low_stock(available, minimum):\n    return True\n\nprint('side effect')",
    "def is_low_stock(available, minimum):\n    return bool(available < minimum)",
    "def is_low_stock(available, minimum):\n    return int(available) < int(minimum)\n\nclass X:\n    pass",
    "def is_low_stock(available, minimum=0):\n    return int(available) < int(minimum)",
    "@staticmethod\ndef is_low_stock(available, minimum):\n    return True",
    "def is_low_stock(available, minimum):\n    return (lambda x: True)(available)",
    "def is_low_stock(available, minimum):\n    available.__class__ = int\n    return True",
]

class IndependentTaskDQA(unittest.TestCase):
    def test_safe_functionally_equivalent_implementations(self):
        for program in VALID:
            with self.subTest(program=program[:48]):
                self.assertEqual(qa_semantic_low_stock(program),program.encode("utf8"))

    def test_unsafe_or_behaviorally_wrong_implementations(self):
        for program in BAD:
            with self.subTest(program=program[:48]):
                with self.assertRaises(QaRejected):
                    qa_semantic_low_stock(program)

    def test_empty_or_oversize_denied(self):
        for program in ("", None, " " * 2049):
            with self.subTest(program_type=type(program).__name__):
                with self.assertRaises(QaRejected):
                    qa_semantic_low_stock(program)

    def test_isolated_code_fence_is_not_exec_before_envelope_validation(self):
        with self.assertRaises(QaRejected):
            qa_semantic_low_stock("\x60\x60\x60python\n" + VALID[0] + "\n\x60\x60\x60")

if __name__=="__main__":
    unittest.main()
