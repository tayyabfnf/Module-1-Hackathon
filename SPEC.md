# SPEC.md — promptlab

Status: pre-implementation. This spec is authoritative; code follows it. Any design change updates this file first (MUST 28).

## 1. Scope & CLI contract (fixed by brief, restated for traceability)

```
promptlab run --suite <file> [--runs N] [--out report.json] [--report]
promptlab compare --baseline <report.json> --candidate <report.json> [--out diff.json]
promptlab doctor
```

Exit codes (global): `0` all cases passed · `1` bad usage / malformed suite / malformed report · `2` one or more cases failed (a **result**, not an error) · `3` model could not be invoked · `4` a suite/report file unreadable.

## 2. Model invocation policy

- **Decision:** the model executable path is resolved from the environment variable `PROMPTLAB_MODEL` (default: `stubmodel.py`, looked up first as a path relative to the CWD, then on `PATH`). Nothing in our code names `stubmodel.py` except this default.
- **Rationale:** the CLI contract in §1 is fixed and must not grow new flags. Judges swap the model binary; an env var is the only zero-footprint way to do that without touching the contract. `doctor` (MUST 18) reports which binary it resolved and whether it responds.
- Every invocation is a subprocess call (MUST 3); stdout is parsed as the one JSON object the contract guarantees (`output`, `tokens_in`, `tokens_out`, `finish`, `latency_ms`). We read only these five keys and assume nothing else about `output`'s shape or content — the hidden "different model binary" suite exists specifically to punish assumptions here.
- `tokens_in` / `tokens_out` / `latency_ms` used in reports are always the values the model process reports, never recomputed by us. The brief's token formula (`ceil(len/4)`) governs text **we** author and must count ourselves (e.g. any token estimate we'd show for truncated failure text) — we do not use it to second-guess the model's own counts.

## 3. Assertion evaluation model

- **Decision:** all assertions in a case's `assert` list are always evaluated, every run. No short-circuit on first failure.
- **Rationale:** MUST 12 requires per-assertion pass/fail counts, and MUST 13 requires failure detail — both are impossible to report completely if we stop early. A case is marked `fail` for a run iff at least one of its assertions failed that run; which one(s) is exactly what the per-assertion counts show.
- Assertion semantics (all eight, fixed by brief):

| type | notes on our implementation |
|---|---|
| `contains` / `not_contains` | substring test on raw `output`; `ignore_case` (default `false`) lowercases both sides first |
| `equals` | exact string equality on raw `output`; `normalize` (default `false`) strips leading/trailing whitespace and collapses internal whitespace runs to a single space before comparing |
| `matches` | `re.search(pattern, output)`; invalid pattern → assertion **fails** with reason `invalid_regex`, does not crash the case or the run (MUST 9) |
| `json_valid` | see §4 |
| `json_field_equals` | operates on the JSON object obtained under the §4 policy; dotted path (`a.b.c`); a path segment that is all digits is treated as a list index, otherwise a dict key; any missing key/index/type mismatch/non-JSON output → assertion fails (not a crash); value comparison is strict JSON-native equality, no type coercion (`"5" != 5`) |
| `max_tokens` | `tokens_out` (from the model's own JSON, §2) `<= value` |
| `finish_is` | `finish == value`, value ∈ `{stop, length, refusal}` |

## 4. Fenced JSON — the `json_valid` decision

- **Decision:** fenced JSON is **not** valid. `json_valid` (and therefore `json_field_equals`, which must stay consistent per the brief) parses `output` as-is with `json.loads`. A response wrapped in ```` ```json ... ``` ```` or bare ```` ``` ... ``` ```` fences fails `json_valid`.
- **Rationale:** the assertion is a proxy for "is this output directly machine-consumable." Silently stripping fences would hide a real, fixable formatting defect — and this project's entire thesis is that harnesses must not quietly smooth over degradations. It also gives `classify_v2.txt` (MUST 19) a concrete, measurable thing to fix: instruct the model not to fence its JSON, and watch `json_valid`'s pass rate move.
- **Rejected alternative:** auto-strip common fence markers before parsing. Defensible, but it would make the assertion test "is there JSON somewhere in here" rather than "is the output well-formed," and it couples the harness to a specific model failure mode instead of measuring the prompt.
- Both `json_valid` and `json_field_equals` use exactly this same parse step, so a fenced response fails both identically.

## 5. Flaky policy (MUST 10, 11)

- **Decision:** per case, `pass_rate = (#runs where the case passed) / runs`. Status is **strict unanimity**, not a threshold:
  - `pass_rate == 1.0` → `pass`
  - `pass_rate == 0.0` → `fail`
  - otherwise → `flaky`
- **Rationale:** any non-unanimous threshold (e.g. "≥0.9 is a pass") needs a number we'd have to defend, and that number's meaning silently changes with `--runs` (0.95 is unreachable at `--runs 2`, and is a single failure out of 20 at `--runs 20`). Unanimity is runs-invariant, requires no arbitrary constant, and matches the brief's own wording in MUST 10 exactly ("passed every run" / "failed every run" / "passed some, failed others").
- **Rejected alternative:** a fixed threshold (e.g. 0.8) or a statistical test (confidence interval on pass rate, per STRETCH 32). Both are more informative but need `--runs` to be large enough to mean anything; at low `--runs` (the hidden suites use `--runs 10`) a threshold degenerates into a small set of achievable fractions and stops being principled. We keep this as the stretch item rather than baking a guessed constant into the core policy.
- A suite-level case is only eligible to be `flaky` if `runs > 1`; at `runs == 1` every case is `pass` or `fail`.
- Exit code for `run`: `2` iff any case's status is `fail` **or** `flaky` (both mean "you cannot trust this case as-is"); `0` iff every case is `pass`.

## 6. Cost accounting

- **Decision:** `totals.tokens_in` / `totals.tokens_out` (report level) are **sums** across every model invocation in the run (all cases × all runs). Per-case `tokens_out_avg` is the **mean per run** for that case.
- **Rationale:** this isn't actually a free choice — the fixed report schema names the per-case field `tokens_out_avg` (implying an average) while the report-level field is plain `tokens_out` with no `_avg` suffix next to a `totals` object holding case/pass/fail counts (which are unambiguously sums). We follow the schema's own naming rather than picking independently.
- `wall_ms` (totals) is the sum of measured wall-clock time across all invocations, computed by us at the point we shell out (not `latency_ms` summed from the model, which is a different, model-reported quantity) — kept out of any determinism check since MUST 8 explicitly isolates timing fields.

## 7. Determinism (MUST 8)

- **Decision:** two `run` invocations of the same suite at `temperature: 0.0` produce byte-identical JSON reports except for `wall_ms` and any per-invocation `latency_ms`-derived value. We achieve this by serializing the report with sorted keys and fixed float formatting, and by zeroing/omitting timing fields from the equality surface judges are expected to diff (they remain present and populated in the actual file — "isolate," not "delete").
- Case and assertion ordering in the report always follows suite-file order, never dict/hash order (this also matters for STRETCH 29 later).

## 8. Suite validation & failure taxonomy (MUST 2, 9)

Every user-facing failure is a single line: `promptlab: <category>: <what> (<where>)`, no traceback, mapped to one exit code:

| category | example message shape | exit |
|---|---|---|
| `usage` | bad flags / missing required arg | 1 |
| `malformed_suite` | missing field, wrong type, unknown assertion type, named with a JSON path like `cases[2].assert[1].field` | 1 |
| `missing_prompt_file` | `prompt_file` does not exist / unreadable | 4 |
| `missing_input_file` | a case's `{"file": ...}` input does not exist / unreadable | 4 |
| `unreadable_report` | `--baseline`/`--candidate` file missing or not JSON | 4 |
| `model_unavailable` | resolved model binary missing / not executable / non-JSON stdout / nonzero unexpected exit | 3 |
| `case_failure` | ≥1 case `fail` or `flaky` (result, not error) | 2 |

Per-assertion runtime problems (invalid regex, non-JSON output for a JSON assertion, missing nested path) are **not** taxonomy errors — they are assertion failures, recorded in `failures` (§9), never abort the run.

## 9. `failures` field content (MUST 13)

Each entry: `{"assertion_type", "expected", "actual", "run_index"}`. `actual` is the relevant slice of `output` (or the parsed field), truncated to 300 characters with a trailing `…(truncated)` marker if longer. This is enough to debug without rerunning, per the brief, without bloating the report.

## 10. Comparison semantics (MUST 14–17)

- **Regression definition (decision):** per case, compare `pass_rate` only (not the `pass`/`fail`/`flaky` label). `candidate.pass_rate < baseline.pass_rate - ε` → `regressed`; `candidate.pass_rate > baseline.pass_rate + ε` → `improved`; otherwise → `unchanged` (ε = 1e-9, float-noise guard only, not a tolerance band). Cases present only in candidate → `new`; only in baseline → `removed`.
- **Rationale:** MUST 15 states explicitly that 1.0 → 0.9 is a regression "even if the case is still labelled a pass" — so the label is disqualified as the basis for comparison and the continuous `pass_rate` is the only correct signal. This also sidesteps ever needing a "how big a drop counts" threshold: any move in the wrong direction is reported as a regression, and the size of the move (the delta) is reported alongside it so a human decides whether it's noise or a real problem. We surface magnitude; we don't hide small regressions.
- **Rejected alternative:** requiring a minimum delta (e.g. 0.05) before calling something a regression. Rejected because "is 0.05 noise" depends on `--runs` (a 0.05 move is 1/20 runs but not reachable at all at `--runs 10` in steps of 0.05... it's 1/10 there too, but the *confidence* behind a 1-run swing is very different at n=10 vs n=200) — baking in a fixed cutoff would misrepresent precision we don't have without also doing STRETCH 32's confidence intervals. Reporting every directional move, with its raw delta, and letting the human weigh it against `--runs`, is the honest option until/unless we build the stretch.
- **Cost delta (MUST 16):** per case and totals, `tokens_in`/`tokens_out` delta and `% change = (candidate - baseline) / baseline * 100`, `null`/omitted if baseline is `0` (avoid div-by-zero).
- **Comparability warnings (MUST 17), non-fatal, printed and included in `diff.json` under a `warnings` array:** same `prompt_hash` on both sides (comparing a prompt against itself); different `suite` names; different `model` settings (temperature/max_tokens). None of these abort the compare — they're advisory, since a judge may deliberately compare across model settings.

## 11. `doctor` (MUST 18)

Checks, each printed pass/fail, exit `0` iff all pass else `1`:
1. Python version ≥ 3.10.
2. Resolved model binary (§2) exists and one trivial invocation returns well-formed JSON on stdout.
3. Suites discoverable: any `*.json` under `./suites` (informational — absence is a warning, not a failure, since hidden suites live elsewhere).
4. All 8 assertion types registered in the evaluator (a self-check against our own dispatch table, catching a broken registration before it costs a demo).

## 12. Report schema conformance

We emit exactly the fields shown in the brief's schema, in that key order, nothing extra, nothing renamed. `prompt_hash` = first 12 hex chars of SHA-256 of the prompt file's raw bytes, computed once per `run` and re-verified (not recomputed differently) by `compare`.

## 13. Definition of done

- `python -m unittest` passes from a fresh clone (MUST 22).
- `promptlab doctor` exits `0` on a fresh clone with the stub model present.
- `promptlab run --suite suites/smoke.json --report` completes and exits `0` or `2` appropriately, with a report byte-stable at `temperature: 0.0` across two runs (§7).
- `promptlab compare` correctly classifies a synthetic baseline/candidate pair covering all five case categories (regressed/improved/unchanged/new/removed) and emits the MUST-17 warnings when triggered.
- All 8 assertion types covered by unit tests, including the invalid-regex and fenced-JSON edge cases.
- `prompts/classify_v2.txt` beats `classify_v1.txt` on the ticket corpus, evidenced only by our own reports (MUST 19–20).
- No path in the CLI contract (§1) can crash the process; every failure mode in §8 is exercised by a test.
- README takes a fresh clone through `doctor` + smoke suite in under 5 minutes.
- This file (SPEC.md) was the first commit, alone (MUST 26), and stays current with every later design change (MUST 28).

## 14. Explicitly rejected alternatives (for the viva, collected)

| decision | rejected alternative | why rejected |
|---|---|---|
| Fenced JSON invalid | Strip fences, then parse | Hides a real prompt defect instead of measuring it |
| Flaky = strict unanimity | Fixed pass-rate threshold | Threshold's meaning isn't stable across `--runs`; needs a defended constant we can't justify at this stage |
| Regression = any `pass_rate` delta, ε only | Minimum-delta threshold (e.g. 0.05) | Same instability across `--runs`; also risks hiding exactly the "silent degradation" MUST 15 says to catch |
| All assertions always evaluated | Short-circuit on first failure | Would break per-assertion counts (MUST 12) and debug detail (MUST 13) |
| Model path via `PROMPTLAB_MODEL` env var | New CLI flag for model path | CLI contract in the brief is fixed ("implement exactly") |

## 15. Addendum — implementation-time decisions not covered above

- **Package layout:** the CLI contract requires an executable literally named `promptlab`. Python packages and files can't share a name in one directory, so the importable code lives in a package called `promptlab_core/`; the repo-root `promptlab` is a thin executable wrapper (`python3 promptlab run ...` or `./promptlab run ...`) that imports and calls it. Tests import `promptlab_core` directly.
- **`compare` exit code (not in the brief's exit table, which is scoped to `run`):** `0` if no case is classified `regressed`, `2` if at least one is (reusing the "result, not error" convention from `run`), `1` for bad usage, `4` for an unreadable/malformed report file. Rationale: lets CI gate on `compare` too, consistent with why `run`'s exit 2 exists at all.
- **Unreadable suite/report vs. malformed:** file missing or unopenable → `unreadable_suite` / `unreadable_report`, exit `4`. File opens but is invalid JSON or fails structural validation → `malformed_suite`, exit `1`. A report that parses as JSON but lacks the required top-level keys is treated as `unreadable_report` (exit `4`), not `malformed_suite`, since compare's inputs are our own generated artifacts, not hand-authored specs.
- **`--call-index`:** always passed as the 0-based run index, letting a seeded model vary output predictably per repeat call within a `--runs N` loop, per the contract's documented flag.
