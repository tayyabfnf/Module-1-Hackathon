# PROMPTS.md — the five most important prompts

Living document — this session has produced two so far; add the next three
(or more) as the build continues (curveball response, MUST 19/20 iteration,
any bug hunts) so the final version has the real five.

## 1. Spec phase kickoff

**Asked:** produce `SPEC.md` for promptlab against the Student Brief,
choosing sensible policies wherever the brief deliberately leaves a decision
open, with rationale defensible in the viva; then a short MUST-requirements
checklist; explicitly told to write no implementation code and to make the
first git commit contain only `SPEC.md`.

**Came back:** a `SPEC.md` covering CLI contract restatement, model-binary
resolution policy, assertion evaluation model (no short-circuit), the
fenced-JSON decision, the flaky policy (strict unanimity, not a threshold),
cost accounting, determinism, a full failure taxonomy, compare semantics,
`doctor` checks, report-schema conformance, a definition of done, and a
table of explicitly rejected alternatives — plus a git repo with exactly one
commit containing only that file, verified with `git log --reverse --stat`.

**Changed:** nothing rejected outright at this stage — this was the first
draft. (Two decisions were pinned down harder than a first pass usually
manages: flaky-as-unanimity and fenced-JSON-invalid were each given a
rejected-alternative row specifically because the brief calls them out as
graded, not just implemented.)

**Why it matters:** MUST 26/27 score zero if the first commit contains any
implementation code, and "spec discipline" is 20% of the grade on its own —
getting this exactly right, first, was worth doing carefully rather than
fast.

## 2. Implementation phase kickoff

**Asked:** "Implement" — a one-word instruction to proceed from spec to
code, in a session already primed with the token-efficiency constraint from
message 1 (limited Claude Code usage).

**Came back:** the full `promptlab_core` package, the `promptlab` executable
wrapper, 37 `unittest` cases (assertions, suite validation, determinism,
seeded-flaky classification, compare classification), a test-only
`fake_model.py` fixture (the real `stubmodel.py` isn't in this sandbox), a
bundled `suites/smoke.json` + demo prompt so `doctor`/`run` work with zero
external files, and `README.md` / `USAGE.md` / `CLAUDE.md`. Verified by
actually running `doctor`, `run`, `compare`, and the full test suite rather
than asserting they'd work.

**Changed:** two things had to be fixed after first writing them: (a) the
package couldn't be named `promptlab` in the same directory as the
`promptlab` executable — a file and a directory can't share a name — so the
package became `promptlab_core`, documented as an addendum in `SPEC.md`
rather than silently patched; (b) an integration test's hand-computed
"expected flaky pattern" was wrong on the first run because it modeled only
one of `fake_model.py`'s two random draws (fencing) and missed the second
(preamble text) — caught by actually running the test suite, not by
inspection.

**Why it matters:** (a) is the kind of naming collision a plan-only review
wouldn't surface — worth recording since MUST 28 says update the spec, don't
just quietly fix it. (b) is a small, concrete instance of the brief's
warning about the "confidently wrong" failure mode: the first version of
that test would have passed by coincidence on some seeds and given false
confidence in the flaky-classification logic; running it and getting a real
assertion failure is what caught it.
