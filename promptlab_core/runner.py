"""Executes a suite and builds a report matching the fixed schema."""
import hashlib
import math
import os

from . import model as model_mod
from .assertions import evaluate
from .errors import PromptlabError

TOKENS_PER_CHAR = 4  # tokens = ceil(len(text) / 4), for text WE author (SPEC §2)


def our_token_estimate(text):
    return math.ceil(len(text) / TOKENS_PER_CHAR) if text else 0


def _prompt_hash(prompt_file):
    with open(prompt_file, "rb") as f:
        digest = hashlib.sha256(f.read()).hexdigest()
    return digest[:12]


def _resolve_input(case, suite_dir):
    inp = case["input"]
    if isinstance(inp, dict):
        path = inp["file"]
        full = path if os.path.isabs(path) else os.path.join(suite_dir, path)
        if not os.path.isfile(full):
            raise PromptlabError("missing_input_file", f"input file not found: {path} (case '{case['id']}')", 4)
        return f"@{os.path.abspath(full)}"
    return inp


def run_suite(suite, suite_dir, runs_override=None, model_path=None):
    prompt_file = suite["prompt_file"]
    full_prompt_path = prompt_file if os.path.isabs(prompt_file) else os.path.join(suite_dir, prompt_file)
    if not os.path.isfile(full_prompt_path):
        raise PromptlabError("missing_prompt_file", f"prompt file not found: {prompt_file}", 4)

    model_path = model_path or model_mod.resolve_model_path()
    model_cfg = suite.get("model", {})
    temperature = model_cfg.get("temperature", 0.0)
    max_tokens = model_cfg.get("max_tokens", 256)
    seed = model_cfg.get("seed")
    runs = runs_override if runs_override is not None else suite.get("runs", 1)

    prompt_hash = _prompt_hash(full_prompt_path)

    case_reports = []
    total_tokens_in = total_tokens_out = 0
    total_wall_ms = 0.0
    passed_n = failed_n = flaky_n = 0

    for case in suite["cases"]:
        input_arg = _resolve_input(case, suite_dir)
        asserts = case["assert"]

        run_pass = []          # bool per run: did the whole case pass that run
        per_assertion = [{"passed": 0, "failed": 0} for _ in asserts]
        failures = []
        tokens_out_runs = []

        for run_idx in range(runs):
            result, wall_ms = model_mod.invoke(
                model_path, full_prompt_path, input_arg, temperature, max_tokens,
                seed=seed, call_index=run_idx,
            )
            total_tokens_in += result["tokens_in"]
            total_tokens_out += result["tokens_out"]
            total_wall_ms += wall_ms
            tokens_out_runs.append(result["tokens_out"])

            case_ok = True
            for j, a in enumerate(asserts):
                ok, expected, actual = evaluate(a, result)
                if ok:
                    per_assertion[j]["passed"] += 1
                else:
                    per_assertion[j]["failed"] += 1
                    case_ok = False
                    failures.append({
                        "assertion_type": a["type"],
                        "expected": expected,
                        "actual": actual,
                        "run_index": run_idx,
                    })
            run_pass.append(case_ok)

        pass_rate = round(sum(run_pass) / runs, 4) if runs else 0.0
        if pass_rate == 1.0:
            status = "pass"
            passed_n += 1
        elif pass_rate == 0.0:
            status = "fail"
            failed_n += 1
        else:
            status = "flaky"
            flaky_n += 1

        case_reports.append({
            "id": case["id"],
            "status": status,
            "pass_rate": pass_rate,
            "tokens_out_avg": round(sum(tokens_out_runs) / runs, 2) if runs else 0,
            "assertions": [
                {"type": asserts[j]["type"], "passed": per_assertion[j]["passed"], "failed": per_assertion[j]["failed"]}
                for j in range(len(asserts))
            ],
            "failures": failures,
        })

    report = {
        "suite": suite["name"],
        "prompt_file": prompt_file,
        "prompt_hash": prompt_hash,
        "runs": runs,
        "model": {"temperature": temperature, "max_tokens": max_tokens},
        "totals": {
            "cases": len(suite["cases"]),
            "passed": passed_n,
            "failed": failed_n,
            "flaky": flaky_n,
            "tokens_in": total_tokens_in,
            "tokens_out": total_tokens_out,
            "wall_ms": round(total_wall_ms, 2),
        },
        "cases": case_reports,
    }
    any_bad = (failed_n > 0) or (flaky_n > 0)
    return report, (2 if any_bad else 0)
