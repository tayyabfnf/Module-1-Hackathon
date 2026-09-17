import unittest

from promptlab_core import compare as C


def make_report(suite, prompt_hash, cases, model=None):
    return {
        "suite": suite, "prompt_file": "p.txt", "prompt_hash": prompt_hash, "runs": 3,
        "model": model or {"temperature": 0.0, "max_tokens": 256},
        "totals": {
            "cases": len(cases), "passed": 0, "failed": 0, "flaky": 0,
            "tokens_in": sum(c.get("tokens_in", 100) for c in cases),
            "tokens_out": sum(c.get("tokens_out", 20) for c in cases),
            "wall_ms": 5,
        },
        "cases": [
            {"id": c["id"], "status": "pass", "pass_rate": c["pass_rate"],
             "tokens_out_avg": c.get("tokens_out_avg", 20), "assertions": [], "failures": []}
            for c in cases
        ],
    }


class TestCompareClassification(unittest.TestCase):
    def test_regressed_improved_unchanged_new_removed(self):
        baseline = make_report("s", "aaa111", [
            {"id": "c1", "pass_rate": 1.0},
            {"id": "c2", "pass_rate": 0.5},
            {"id": "c3", "pass_rate": 1.0},
            {"id": "c4", "pass_rate": 1.0},
        ])
        candidate = make_report("s", "bbb222", [
            {"id": "c1", "pass_rate": 0.9},   # regressed (still a "pass" under unanimity would be false actually 0.9!=1.0 so flaky in real runner, but here just testing pass_rate compare)
            {"id": "c2", "pass_rate": 1.0},   # improved
            {"id": "c3", "pass_rate": 1.0},   # unchanged
            {"id": "c5", "pass_rate": 1.0},   # new
            # c4 removed
        ])
        diff = C.compare(baseline, candidate)
        by_id = {c["id"]: c["classification"] for c in diff["cases"]}
        self.assertEqual(by_id["c1"], "regressed")
        self.assertEqual(by_id["c2"], "improved")
        self.assertEqual(by_id["c3"], "unchanged")
        self.assertEqual(by_id["c5"], "new")
        self.assertEqual(by_id["c4"], "removed")
        self.assertEqual(diff["summary"], {"regressed": 1, "improved": 1, "unchanged": 1, "new": 1, "removed": 1})

    def test_small_silent_regression_still_flagged(self):
        # MUST 15: 1.0 -> 0.9 is a regression even though both could be labelled "pass"-ish.
        baseline = make_report("s", "h1", [{"id": "c1", "pass_rate": 1.0}])
        candidate = make_report("s", "h2", [{"id": "c1", "pass_rate": 0.9}])
        diff = C.compare(baseline, candidate)
        self.assertEqual(diff["cases"][0]["classification"], "regressed")

    def test_same_prompt_hash_warns(self):
        baseline = make_report("s", "same", [{"id": "c1", "pass_rate": 1.0}])
        candidate = make_report("s", "same", [{"id": "c1", "pass_rate": 1.0}])
        diff = C.compare(baseline, candidate)
        self.assertTrue(any("prompt_hash" in w for w in diff["warnings"]))

    def test_different_suite_warns(self):
        baseline = make_report("suiteA", "h1", [{"id": "c1", "pass_rate": 1.0}])
        candidate = make_report("suiteB", "h2", [{"id": "c1", "pass_rate": 1.0}])
        diff = C.compare(baseline, candidate)
        self.assertTrue(any("different suites" in w for w in diff["warnings"]))

    def test_different_model_settings_warns(self):
        baseline = make_report("s", "h1", [{"id": "c1", "pass_rate": 1.0}], model={"temperature": 0.0, "max_tokens": 256})
        candidate = make_report("s", "h2", [{"id": "c1", "pass_rate": 1.0}], model={"temperature": 0.7, "max_tokens": 256})
        diff = C.compare(baseline, candidate)
        self.assertTrue(any("different model settings" in w for w in diff["warnings"]))

    def test_cost_delta_percentage(self):
        baseline = make_report("s", "h1", [{"id": "c1", "pass_rate": 1.0, "tokens_out": 100}])
        candidate = make_report("s", "h2", [{"id": "c1", "pass_rate": 1.0, "tokens_out": 150}])
        diff = C.compare(baseline, candidate)
        self.assertEqual(diff["totals"]["tokens_out"]["delta"], 50)
        self.assertEqual(diff["totals"]["tokens_out"]["pct_change"], 50.0)


if __name__ == "__main__":
    unittest.main()
