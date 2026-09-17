# CLAUDE.md — context for Claude Code working in this repo

## What this is

`promptlab`: a stdlib-only CLI test runner for prompts (Module 1 Hackathon).
**`SPEC.md` is the source of truth.** If this file and `SPEC.md` ever
disagree, `SPEC.md` wins — update it first, then the code (spec-driven
development is graded; see SPEC.md §13, MUST 26–28).

## Hard constraints — do not violate these

- Python **3.10+ standard library only**. No pip installs, no `pytest`,
  no `yaml`, no `rich`. `unittest` only for tests.
- **Never import, copy, or reimplement `stubmodel.py`** (or whatever
  `PROMPTLAB_MODEL` points at). Every model call goes through
  `promptlab_core/model.py`'s subprocess invocation. A hidden judging suite
  swaps in a different model binary with the same CLI contract — any code
  that assumes something about *what* the model says (not just the JSON
  shape it's contractually required to return) is a bug.
- The CLI contract (`promptlab run|compare|doctor` with exactly the flags in
  SPEC.md §1) is fixed. Don't add new required flags to satisfy an internal
  need — solve it another way (see SPEC.md §2 for why model-binary selection
  is an env var, not a flag).
- No crash may reach the user (MUST 9). Every failure path returns through
  `PromptlabError` with a category and one of the five exit codes
  (SPEC.md §8) — never let an exception escape `cli.main`.
- Report JSON must match the brief's schema exactly (field names, order,
  types). Don't rename or add top-level fields without updating SPEC.md.

## Where things live

- `promptlab_core/` — package (`assertions.py`, `suite.py`, `model.py`,
  `runner.py`, `reporter.py`, `compare.py`, `doctor.py`, `cli.py`, `errors.py`).
- `promptlab` (root, executable) — thin wrapper calling `promptlab_core.cli.main`.
  It's a separate name from the package on purpose (a file and a directory
  can't share a name) — see SPEC.md §15.
- `tests/` — `unittest`, using `tests/fixtures/fake_model.py` (our own
  stand-in for the real `stubmodel.py`, which this sandbox doesn't have —
  swap `PROMPTLAB_MODEL` to the real one once it's added to the repo).
- `suites/smoke.json` + `examples/demo_prompt.txt` — a bundled runnable demo
  independent of the real starter kit, so `doctor`/`run` work immediately.
- `prompts/classify_v1.txt` → `classify_v2.txt`, `data/tickets.json`,
  `IMPROVEMENT.md` — MUST 19/20 work; **not started yet**, needs the real
  starter-kit files dropped in first.

## Before changing a policy decision

Every "we chose X over Y" in SPEC.md (flaky threshold, fenced-JSON, cost
accounting, regression definition, assertion short-circuit, model-path
resolution) has a rejected alternative recorded in SPEC.md §14. If you want
to change one, update that table's rationale, don't just change the code —
the viva will ask why, and "Claude changed it" is not an acceptable answer
(brief: "you own every line you submit").

## Workflow

1. Read `SPEC.md` before touching `promptlab_core/`.
2. Run `python3 -m unittest` after any change — it's fast and covers
   assertions, suite validation, determinism, and flaky classification.
3. Sanity-check with `PROMPTLAB_MODEL=tests/fixtures/fake_model.py ./promptlab doctor`
   and `... run --suite suites/smoke.json --report`.
4. When the design changes, edit `SPEC.md` in the same work session, before
   or in the same commit as the code change — never after.
