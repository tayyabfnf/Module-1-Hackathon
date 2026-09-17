"""compare: classify every case between two reports (MUST 14-17)."""
import json
import os

from .errors import PromptlabError

EPS = 1e-9
REQUIRED_KEYS = ("suite", "prompt_file", "prompt_hash", "runs", "model", "totals", "cases")


def load_report(path):
    if not os.path.isfile(path):
        raise PromptlabError("unreadable_report", f"report file not found: {path}", 4)
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        raise PromptlabError("unreadable_report", f"cannot read report {path}: {e}", 4)
    if not isinstance(data, dict) or any(k not in data for k in REQUIRED_KEYS):
        raise PromptlabError("unreadable_report", f"{path} is not a valid promptlab report", 4)
    return data


def _pct(base, cand):
    if base == 0:
        return None
    return round((cand - base) / base * 100, 2)


def compare(baseline, candidate):
    warnings = []
    if baseline["prompt_hash"] == candidate["prompt_hash"]:
        warnings.append("baseline and candidate share the same prompt_hash — comparing a prompt against itself")
    if baseline["suite"] != candidate["suite"]:
        warnings.append(f"different suites: '{baseline['suite']}' vs '{candidate['suite']}'")
    if baseline["model"] != candidate["model"]:
        warnings.append(f"different model settings: {baseline['model']} vs {candidate['model']}")

    base_cases = {c["id"]: c for c in baseline["cases"]}
    cand_cases = {c["id"]: c for c in candidate["cases"]}
    all_ids = list(dict.fromkeys(list(base_cases) + list(cand_cases)))

    case_diffs = []
    summary = {"regressed": 0, "improved": 0, "unchanged": 0, "new": 0, "removed": 0}
    for cid in all_ids:
        b, c = base_cases.get(cid), cand_cases.get(cid)
        if b is None:
            classification = "new"
        elif c is None:
            classification = "removed"
        else:
            delta = c["pass_rate"] - b["pass_rate"]
            if delta < -EPS:
                classification = "regressed"
            elif delta > EPS:
                classification = "improved"
            else:
                classification = "unchanged"
        summary[classification] += 1

        entry = {"id": cid, "classification": classification}
        if b is not None:
            entry["baseline_pass_rate"] = b["pass_rate"]
            entry["baseline_tokens_out_avg"] = b["tokens_out_avg"]
        if c is not None:
            entry["candidate_pass_rate"] = c["pass_rate"]
            entry["candidate_tokens_out_avg"] = c["tokens_out_avg"]
        if b is not None and c is not None:
            entry["pass_rate_delta"] = round(c["pass_rate"] - b["pass_rate"], 4)
            entry["tokens_out_avg_delta"] = round(c["tokens_out_avg"] - b["tokens_out_avg"], 2)
            entry["tokens_out_avg_pct_change"] = _pct(b["tokens_out_avg"], c["tokens_out_avg"])
        case_diffs.append(entry)

    bt, ct = baseline["totals"], candidate["totals"]
    totals_delta = {}
    for key in ("tokens_in", "tokens_out"):
        totals_delta[key] = {
            "baseline": bt[key], "candidate": ct[key],
            "delta": ct[key] - bt[key], "pct_change": _pct(bt[key], ct[key]),
        }

    return {
        "baseline": {"suite": baseline["suite"], "prompt_hash": baseline["prompt_hash"]},
        "candidate": {"suite": candidate["suite"], "prompt_hash": candidate["prompt_hash"]},
        "warnings": warnings,
        "totals": totals_delta,
        "summary": summary,
        "cases": case_diffs,
    }


def human_summary(diff):
    s = diff["summary"]
    lines = [
        f"compare: regressed={s['regressed']} improved={s['improved']} unchanged={s['unchanged']} "
        f"new={s['new']} removed={s['removed']}",
    ]
    for w in diff["warnings"]:
        lines.append(f"  warning: {w}")
    for c in diff["cases"]:
        if c["classification"] == "regressed":
            lines.append(f"  regressed: {c['id']} pass_rate {c['baseline_pass_rate']} -> {c['candidate_pass_rate']}")
    return "\n".join(lines)
