"""Suite file loading and validation."""
import json
import os

from .errors import PromptlabError

ASSERTION_SPECS = {
    "contains": {"required": ["value"], "optional": ["ignore_case"]},
    "not_contains": {"required": ["value"], "optional": ["ignore_case"]},
    "equals": {"required": ["value"], "optional": ["normalize"]},
    "matches": {"required": ["pattern"], "optional": []},
    "json_valid": {"required": [], "optional": []},
    "json_field_equals": {"required": ["field", "value"], "optional": []},
    "max_tokens": {"required": ["value"], "optional": []},
    "finish_is": {"required": ["value"], "optional": []},
}


def _malformed(where, what):
    raise PromptlabError("malformed_suite", f"{what} ({where})", 1)


def load_suite(path):
    """Read, parse and validate a suite file. Returns (suite_dict, suite_dir)."""
    if not os.path.isfile(path):
        raise PromptlabError("unreadable_suite", f"suite file not found: {path}", 4)
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = f.read()
    except OSError as e:
        raise PromptlabError("unreadable_suite", f"cannot read {path}: {e}", 4)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise PromptlabError("malformed_suite", f"invalid JSON: {e}", 1)

    validate_suite(data)
    return data, os.path.dirname(os.path.abspath(path))


def validate_suite(data):
    if not isinstance(data, dict):
        _malformed("<root>", "suite must be a JSON object")

    for field, typ in (("name", str), ("prompt_file", str)):
        if field not in data:
            _malformed("<root>", f"missing required field '{field}'")
        if not isinstance(data[field], typ):
            _malformed(field, f"'{field}' must be a string")

    if "cases" not in data:
        _malformed("<root>", "missing required field 'cases'")
    if not isinstance(data["cases"], list):
        _malformed("cases", "'cases' must be a list")

    if "runs" in data and (not isinstance(data["runs"], int) or isinstance(data["runs"], bool) or data["runs"] < 1):
        _malformed("runs", "'runs' must be a positive integer")

    if "model" in data:
        model = data["model"]
        if not isinstance(model, dict):
            _malformed("model", "'model' must be an object")
        if "temperature" in model and not isinstance(model["temperature"], (int, float)):
            _malformed("model.temperature", "'temperature' must be a number")
        if "max_tokens" in model and (not isinstance(model["max_tokens"], int) or isinstance(model["max_tokens"], bool)):
            _malformed("model.max_tokens", "'max_tokens' must be an integer")
        if "seed" in model and not isinstance(model["seed"], int):
            _malformed("model.seed", "'seed' must be an integer")

    seen_ids = set()
    for i, case in enumerate(data["cases"]):
        where = f"cases[{i}]"
        if not isinstance(case, dict):
            _malformed(where, "each case must be an object")
        if "id" not in case or not isinstance(case["id"], str) or not case["id"]:
            _malformed(f"{where}.id", "each case needs a non-empty string 'id'")
        if case["id"] in seen_ids:
            _malformed(f"{where}.id", f"duplicate case id '{case['id']}'")
        seen_ids.add(case["id"])

        if "input" not in case:
            _malformed(f"{where}.input", "missing required field 'input'")
        inp = case["input"]
        if isinstance(inp, dict):
            if "file" not in inp or not isinstance(inp["file"], str):
                _malformed(f"{where}.input", "file-input must be {'file': <string path>}")
        elif not isinstance(inp, str):
            _malformed(f"{where}.input", "'input' must be a string or {'file': <path>}")

        if "assert" not in case:
            _malformed(f"{where}.assert", "missing required field 'assert' (use [] for none)")
        asserts = case["assert"]
        if not isinstance(asserts, list):
            _malformed(f"{where}.assert", "'assert' must be a list")

        for j, a in enumerate(asserts):
            awhere = f"{where}.assert[{j}]"
            if not isinstance(a, dict) or "type" not in a:
                _malformed(awhere, "each assertion needs a 'type'")
            if a["type"] not in ASSERTION_SPECS:
                _malformed(f"{awhere}.type", f"unknown assertion type '{a['type']}'")
            spec = ASSERTION_SPECS[a["type"]]
            for req in spec["required"]:
                if req not in a:
                    _malformed(awhere, f"assertion type '{a['type']}' requires field '{req}'")
