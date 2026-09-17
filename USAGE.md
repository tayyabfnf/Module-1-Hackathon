# USAGE.md — for an agent running promptlab unattended

You are an agent invoking this CLI with no human watching. This document
tells you what to run, how to read the result, and what to do next for each
outcome. Do not guess at behavior not stated here — see `SPEC.md` for the
full policy, this file for the operational summary.

## Before anything: `doctor`

Always run `promptlab doctor` first in a new environment.

```
promptlab doctor
```

- Exit `0`: environment is sane. Proceed.
- Exit `1`: read the `[FAIL]` lines it printed to stdout. The most likely
  cause is `PROMPTLAB_MODEL` unset or pointing at a missing file — set it to
  the model binary's path and re-run `doctor` before doing anything else.
  Do not attempt `run` until `doctor` exits `0`.

## Running a suite

```
promptlab run --suite <path> [--runs N] [--out report.json] [--report]
```

- Always pass `--out` when you intend to consume the result programmatically
  (parse it), so you get a stable file path instead of stdout mixed with
  whatever else is on the pipe. Add `--report` if a human will also read the
  terminal — the machine JSON goes to the `--out` file or stdout either way;
  `--report`'s summary always goes to stderr and never mixes into the JSON.
- `--runs N` overrides the suite file's own `runs`. Use `--runs 1` for a fast
  sanity check; use a higher `N` (10+) when you need to trust a `flaky`
  verdict — at `--runs 1` no case can ever be reported `flaky`, only `pass`
  or `fail`, and that is a much weaker guarantee.

### Reading the exit code — decide your next action here, not by parsing text

| exit | meaning | what you should do |
|---|---|---|
| `0` | every case passed every run | proceed; nothing to fix |
| `1` | bad flags, or the suite file itself is invalid (missing/wrong-typed field, unknown assertion type) | **do not retry as-is** — fix the suite file per the one-line message (it names the field and location), then re-run |
| `2` | the suite ran fine, but ≥1 case is `fail` or `flaky` | **this is a result, not a crash.** Open the report's `cases[].failures` for the specific case(s); do not just retry hoping for green — a `fail` won't change, and reporting a `flaky` case as passing is exactly the mistake this tool exists to prevent. Decide (or ask) whether the prompt needs work before proceeding |
| `3` | the model binary could not be invoked or returned something the harness couldn't use | check `PROMPTLAB_MODEL` and that the binary is executable / on `PATH`; do not treat this as "the prompt is bad" — it's an environment problem |
| `4` | a suite or report file was missing/unreadable | check the path you passed; this is a filesystem problem, not a suite-content problem (that's `1`) |

Never treat exit `2` as failure of the *command* — the command succeeded at
its job of measuring. Treat exit `1`, `3`, `4` as things you must fix before
the measurement can even happen.

## Reading a report (when you have one, e.g. from `--out`)

- `totals.passed / failed / flaky / cases` — the headline. `flaky` is its
  own bucket, not folded into either pass or fail; a case there passed some
  runs and failed others (see `SPEC.md` §5) — don't average it away.
- Per case, `pass_rate` is the precise number; `status` is the derived label
  under this project's policy (unanimity: 1.0→pass, 0.0→fail, else flaky).
  If you're deciding whether a change helped, always compare `pass_rate`
  between two reports, never just the label (see `compare` below).
- `cases[].failures` has everything needed to explain a failure without
  re-running: which assertion, what was expected, what the output actually
  was (truncated). Use this instead of re-invoking the model to "see what
  happened."

## Comparing two reports

```
promptlab compare --baseline old.json --candidate new.json [--out diff.json]
```

- Exit `0`: no case regressed. Exit `2`: at least one case did — check
  `diff.json`'s `cases[]` entries with `"classification": "regressed"`, and
  the `pass_rate_delta` there, before deciding a change is safe to keep.
- **Read `warnings` before trusting the diff at all.** If it warns the two
  reports share a `prompt_hash`, come from different suites, or used
  different model settings, the comparison may not mean what it looks like —
  don't report "regressed"/"improved" to a human without surfacing that
  warning alongside it.
- A case can be `regressed` even while both reports call it `pass` under the
  unanimity policy (e.g. 1.0 → 0.95 isn't literally possible under strict
  unanimity at some `--runs`, but 1.0 → 0.9 *is* a regression regardless of
  either side's label) — always look at `pass_rate_delta`, not just labels.

## What not to do

- Don't parse the human `--report` summary (stderr) as your source of truth
  — it's for people. Parse the JSON (`--out` file, or stdout when `--out` is
  omitted).
- Don't retry a `2` exit expecting a different result at the same `--runs` —
  temperature-0 cases are deterministic (identical result every time); only
  a suite/prompt/`--runs` change can move the outcome.
- Don't suppress or "fix" a `flaky` result by re-running until it passes.
  That is precisely the behavior this project exists to catch.
