import json
import os
import tempfile
import unittest

from promptlab_core import suite as S
from promptlab_core.errors import PromptlabError


def write_suite(obj):
    fd, path = tempfile.mkstemp(suffix=".json")
    with os.fdopen(fd, "w") as f:
        json.dump(obj, f)
    return path


VALID = {
    "name": "t",
    "prompt_file": "p.txt",
    "cases": [{"id": "c1", "input": "hi", "assert": [{"type": "contains", "value": "hi"}]}],
}


class TestSuiteValidation(unittest.TestCase):
    def test_valid_suite_loads(self):
        path = write_suite(VALID)
        suite, suite_dir = S.load_suite(path)
        self.assertEqual(suite["name"], "t")

    def test_missing_file_is_exit4(self):
        with self.assertRaises(PromptlabError) as ctx:
            S.load_suite("/no/such/file.json")
        self.assertEqual(ctx.exception.exit_code, 4)

    def test_invalid_json_is_exit1(self):
        fd, path = tempfile.mkstemp(suffix=".json")
        with os.fdopen(fd, "w") as f:
            f.write("{not json")
        with self.assertRaises(PromptlabError) as ctx:
            S.load_suite(path)
        self.assertEqual(ctx.exception.exit_code, 1)

    def test_missing_required_field(self):
        bad = {"prompt_file": "p.txt", "cases": []}
        with self.assertRaises(PromptlabError) as ctx:
            S.validate_suite(bad)
        self.assertEqual(ctx.exception.category, "malformed_suite")

    def test_unknown_assertion_type(self):
        bad = json.loads(json.dumps(VALID))
        bad["cases"][0]["assert"][0]["type"] = "nonsense"
        with self.assertRaises(PromptlabError):
            S.validate_suite(bad)

    def test_assertion_missing_required_field(self):
        bad = json.loads(json.dumps(VALID))
        bad["cases"][0]["assert"][0] = {"type": "contains"}  # missing 'value'
        with self.assertRaises(PromptlabError):
            S.validate_suite(bad)

    def test_empty_suite_is_valid(self):
        empty = {"name": "empty", "prompt_file": "p.txt", "cases": []}
        S.validate_suite(empty)  # must not raise

    def test_case_with_zero_assertions_is_valid(self):
        s = {"name": "t", "prompt_file": "p.txt", "cases": [{"id": "c1", "input": "hi", "assert": []}]}
        S.validate_suite(s)  # must not raise

    def test_duplicate_case_id_rejected(self):
        s = json.loads(json.dumps(VALID))
        s["cases"].append(json.loads(json.dumps(s["cases"][0])))
        with self.assertRaises(PromptlabError):
            S.validate_suite(s)


if __name__ == "__main__":
    unittest.main()
