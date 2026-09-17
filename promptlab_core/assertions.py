"""The eight assertion types. Each check_* returns (passed, expected, actual)."""
import json
import re

_TRUNC = 300


def _truncate(s):
    s = str(s)
    return s if len(s) <= _TRUNC else s[:_TRUNC] + "\u2026(truncated)"


def _norm_ws(s):
    return re.sub(r"\s+", " ", s.strip())


def _parse_json_strict(text):
    """SPEC §4: fenced JSON is not valid. Parse the raw output as-is."""
    return json.loads(text)


def _resolve_path(obj, path):
    cur = obj
    for part in path.split("."):
        if isinstance(cur, list):
            if not part.lstrip("-").isdigit():
                raise KeyError(path)
            idx = int(part)
            if idx < 0 or idx >= len(cur):
                raise KeyError(path)
            cur = cur[idx]
        elif isinstance(cur, dict):
            if part not in cur:
                raise KeyError(path)
            cur = cur[part]
        else:
            raise KeyError(path)
    return cur


def check_contains(a, result):
    value, text = a["value"], result["output"]
    if a.get("ignore_case"):
        value, text = value.lower(), text.lower()
    return (value in text), a["value"], _truncate(result["output"])


def check_not_contains(a, result):
    value, text = a["value"], result["output"]
    if a.get("ignore_case"):
        value, text = value.lower(), text.lower()
    return (value not in text), a["value"], _truncate(result["output"])


def check_equals(a, result):
    value, text = a["value"], result["output"]
    if a.get("normalize"):
        value, text = _norm_ws(value), _norm_ws(text)
    return (text == value), a["value"], _truncate(result["output"])


def check_matches(a, result):
    try:
        found = re.search(a["pattern"], result["output"]) is not None
        return found, a["pattern"], _truncate(result["output"])
    except re.error as e:
        return False, a["pattern"], f"<invalid regex: {e}>"


def check_json_valid(a, result):
    try:
        _parse_json_strict(result["output"])
        return True, "valid JSON", _truncate(result["output"])
    except (json.JSONDecodeError, TypeError):
        return False, "valid JSON", _truncate(result["output"])


def check_json_field_equals(a, result):
    try:
        obj = _parse_json_strict(result["output"])
        actual = _resolve_path(obj, a["field"])
        return (actual == a["value"]), a["value"], _truncate(json.dumps(actual))
    except (json.JSONDecodeError, TypeError):
        return False, a["value"], "<output is not valid JSON>"
    except KeyError:
        return False, a["value"], f"<field '{a['field']}' not found>"


def check_max_tokens(a, result):
    return (result["tokens_out"] <= a["value"]), a["value"], result["tokens_out"]


def check_finish_is(a, result):
    return (result["finish"] == a["value"]), a["value"], result["finish"]


DISPATCH = {
    "contains": check_contains,
    "not_contains": check_not_contains,
    "equals": check_equals,
    "matches": check_matches,
    "json_valid": check_json_valid,
    "json_field_equals": check_json_field_equals,
    "max_tokens": check_max_tokens,
    "finish_is": check_finish_is,
}


def evaluate(assertion, model_result):
    """Returns (passed: bool, expected, actual). Never raises (SPEC §3/§9)."""
    fn = DISPATCH[assertion["type"]]
    return fn(assertion, model_result)
