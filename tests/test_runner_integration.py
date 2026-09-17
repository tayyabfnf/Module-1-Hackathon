import copy
import json
import os
import random
import tempfile
import unittest

from promptlab_core import runner
from promptlab_core import suite as S

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")
FAKE_MODEL = os.path.join(FIXTURES, "fake_model.py")


def write(path, content):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def strip_timing(report):
    r = copy.deepcopy(report)
    r["totals"].pop("wall_ms", None)
    return r


class TestDeterminismAtTempZero(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        write(os.path.join(self.dir, "prompt.txt"), "classify the ticket")
        self.suite = {
            "name": "det",
            "prompt_file": "prompt.txt",
            "model": {"temperature": 0.0, "max_tokens": 64},
            "runs": 3,
            "cases": [{
                "id": "c1", "input": "I was charged twice for invoice 7",
                "assert": [{"type": "json_valid"}, {"type": "json_field_equals", "field": "category", "value": "billing"}],
            }],
        }

    def test_two_runs_are_byte_identical_apart_from_timing(self):
        r1, _ = runner.run_suite(self.suite, self.dir, model_path=FAKE_MODEL)
        r2, _ = runner.run_suite(self.suite, self.dir, model_path=FAKE_MODEL)
        self.assertEqual(strip_timing(r1), strip_timing(r2))
        self.assertEqual(r1["cases"][0]["status"], "pass")
        self.assertEqual(r1["cases"][0]["pass_rate"], 1.0)


class TestFlakyClassification(unittest.TestCase):
    """Reproduces fake_model's own seeded RNG to derive the expected per-run
    outcome independently, then checks the harness's aggregation matches."""

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        write(os.path.join(self.dir, "prompt.txt"), "classify the ticket")
        self.seed = 42
        self.runs = 6
        self.suite = {
            "name": "flaky-test",
            "prompt_file": "prompt.txt",
            "model": {"temperature": 0.5, "max_tokens": 64, "seed": self.seed},
            "runs": self.runs,
            "cases": [{"id": "c1", "input": "I was charged twice", "assert": [{"type": "json_valid"}]}],
        }

    def expected_pass_per_run(self):
        # Mirrors fake_model.py's two independent rng draws exactly (fence, then preamble).
        expected = []
        for call_index in range(self.runs):
            rng = random.Random(self.seed + call_index)
            fenced = rng.random() < 0.5
            prefixed = rng.random() < 0.3
            expected.append(not fenced and not prefixed)  # either one breaks json_valid
        return expected

    def test_status_and_pass_rate_match_expected(self):
        report, _ = runner.run_suite(self.suite, self.dir, model_path=FAKE_MODEL)
        expected = self.expected_pass_per_run()
        expected_rate = round(sum(expected) / self.runs, 4)
        case = report["cases"][0]
        self.assertEqual(case["pass_rate"], expected_rate)
        if expected_rate == 1.0:
            self.assertEqual(case["status"], "pass")
        elif expected_rate == 0.0:
            self.assertEqual(case["status"], "fail")
        else:
            self.assertEqual(case["status"], "flaky")
        # per-assertion counts must sum to `runs`
        a = case["assertions"][0]
        self.assertEqual(a["passed"] + a["failed"], self.runs)
        self.assertEqual(a["passed"], sum(expected))


class TestZeroAssertionCasePassesVacuously(unittest.TestCase):
    def test_no_assertions_means_pass(self):
        d = tempfile.mkdtemp()
        write(os.path.join(d, "prompt.txt"), "x")
        suite = {
            "name": "s", "prompt_file": "prompt.txt", "runs": 1,
            "cases": [{"id": "c1", "input": "hello", "assert": []}],
        }
        report, exit_code = runner.run_suite(suite, d, model_path=FAKE_MODEL)
        self.assertEqual(report["cases"][0]["status"], "pass")
        self.assertEqual(exit_code, 0)


class TestFinishIsRefusal(unittest.TestCase):
    def test_refusal_detected(self):
        d = tempfile.mkdtemp()
        write(os.path.join(d, "prompt.txt"), "x")
        suite = {
            "name": "s", "prompt_file": "prompt.txt", "runs": 1,
            "cases": [{"id": "c1", "input": "REFUSE_ME please", "assert": [{"type": "finish_is", "value": "refusal"}]}],
        }
        report, exit_code = runner.run_suite(suite, d, model_path=FAKE_MODEL)
        self.assertEqual(report["cases"][0]["status"], "pass")
        self.assertEqual(exit_code, 0)


if __name__ == "__main__":
    unittest.main()
