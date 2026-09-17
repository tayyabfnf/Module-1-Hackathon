import unittest

from promptlab_core import assertions as A


def R(output, tokens_out=10, finish="stop", tokens_in=5):
    return {"output": output, "tokens_out": tokens_out, "finish": finish, "tokens_in": tokens_in}


class TestContains(unittest.TestCase):
    def test_contains_pass(self):
        ok, *_ = A.evaluate({"type": "contains", "value": "hello"}, R("hello world"))
        self.assertTrue(ok)

    def test_contains_fail(self):
        ok, *_ = A.evaluate({"type": "contains", "value": "xyz"}, R("hello world"))
        self.assertFalse(ok)

    def test_contains_ignore_case(self):
        ok, *_ = A.evaluate({"type": "contains", "value": "HELLO", "ignore_case": True}, R("hello world"))
        self.assertTrue(ok)

    def test_not_contains(self):
        ok, *_ = A.evaluate({"type": "not_contains", "value": "Sure"}, R("hello world"))
        self.assertTrue(ok)
        ok, *_ = A.evaluate({"type": "not_contains", "value": "hello"}, R("hello world"))
        self.assertFalse(ok)


class TestEquals(unittest.TestCase):
    def test_equals_strict(self):
        ok, *_ = A.evaluate({"type": "equals", "value": "hi"}, R(" hi "))
        self.assertFalse(ok)

    def test_equals_normalized(self):
        ok, *_ = A.evaluate({"type": "equals", "value": "hi there", "normalize": True}, R("  hi   there  "))
        self.assertTrue(ok)


class TestMatches(unittest.TestCase):
    def test_matches_pass(self):
        ok, *_ = A.evaluate({"type": "matches", "pattern": r"\d{3}-\d{4}"}, R("call 555-1234 now"))
        self.assertTrue(ok)

    def test_invalid_regex_fails_not_crashes(self):
        ok, expected, actual = A.evaluate({"type": "matches", "pattern": "("}, R("anything"))
        self.assertFalse(ok)
        self.assertIn("invalid regex", actual)


class TestJsonValid(unittest.TestCase):
    def test_bare_json_valid(self):
        ok, *_ = A.evaluate({"type": "json_valid"}, R('{"a": 1}'))
        self.assertTrue(ok)

    def test_fenced_json_is_not_valid(self):
        # SPEC.md §4: fenced JSON deliberately fails json_valid.
        ok, *_ = A.evaluate({"type": "json_valid"}, R('```json\n{"a": 1}\n```'))
        self.assertFalse(ok)

    def test_garbage_not_valid(self):
        ok, *_ = A.evaluate({"type": "json_valid"}, R("not json at all"))
        self.assertFalse(ok)


class TestJsonFieldEquals(unittest.TestCase):
    def test_top_level_field(self):
        ok, *_ = A.evaluate(
            {"type": "json_field_equals", "field": "category", "value": "billing"},
            R('{"category": "billing"}'),
        )
        self.assertTrue(ok)

    def test_nested_path(self):
        ok, *_ = A.evaluate(
            {"type": "json_field_equals", "field": "meta.tags.0", "value": "urgent"},
            R('{"meta": {"tags": ["urgent", "billing"]}}'),
        )
        self.assertTrue(ok)

    def test_missing_field_fails_not_crashes(self):
        ok, *_ = A.evaluate(
            {"type": "json_field_equals", "field": "nope", "value": "x"},
            R('{"category": "billing"}'),
        )
        self.assertFalse(ok)

    def test_fenced_json_fails_consistently_with_json_valid(self):
        ok, *_ = A.evaluate(
            {"type": "json_field_equals", "field": "category", "value": "billing"},
            R('```{"category": "billing"}```'),
        )
        self.assertFalse(ok)

    def test_no_type_coercion(self):
        ok, *_ = A.evaluate(
            {"type": "json_field_equals", "field": "count", "value": 5},
            R('{"count": "5"}'),
        )
        self.assertFalse(ok)


class TestMaxTokensAndFinish(unittest.TestCase):
    def test_max_tokens(self):
        ok, *_ = A.evaluate({"type": "max_tokens", "value": 40}, R("x", tokens_out=40))
        self.assertTrue(ok)
        ok, *_ = A.evaluate({"type": "max_tokens", "value": 40}, R("x", tokens_out=41))
        self.assertFalse(ok)

    def test_finish_is(self):
        ok, *_ = A.evaluate({"type": "finish_is", "value": "stop"}, R("x", finish="stop"))
        self.assertTrue(ok)
        ok, *_ = A.evaluate({"type": "finish_is", "value": "stop"}, R("x", finish="length"))
        self.assertFalse(ok)


if __name__ == "__main__":
    unittest.main()
