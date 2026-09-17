# promptlab

A stdlib-only CLI test runner for prompts. See `SPEC.md` for the design and
every policy decision (flaky threshold, fenced-JSON, regression definition,
etc.) with rationale.

## Layout

- `promptlab` — the executable entry point (`./promptlab run ...`).
- `promptlab_core/` — the importable package (named separately from the
  executable so the two can coexist in one directory — see SPEC.md §15).
- `suites/`, `examples/` — a bundled demo suite/prompt that runs against the
  test-only fake model, so `doctor` + a smoke run work with **no external
  model file needed**.
- `tests/` — `unittest` suite for the harness itself, using
  `tests/fixtures/fake_model.py` (a small stand-in implementing the same CLI
  contract as the brief's `stubmodel.py`, used only so our tests don't
  depend on a file we weren't given in this environment).
- `prompts/classify_v1.txt`, `prompts/classify_v2.txt`, `data/tickets.json`,
  and the real `stubmodel.py` are the **starter-kit files** — drop them in
  from the official kit before doing the MUST 19/20 prompt-improvement work;
  they are not part of this commit.

## Quickstart

```bash
# point the harness at whichever model binary implements the CLI contract
export PROMPTLAB_MODEL=./stubmodel.py        # or tests/fixtures/fake_model.py to try it now

./promptlab doctor
./promptlab run --suite suites/smoke.json --report
./promptlab run --suite suites/smoke.json --out /tmp/baseline.json
./promptlab compare --baseline /tmp/baseline.json --candidate /tmp/baseline.json

python3 -m unittest        # runs tests/, no external model needed
```

## Exit codes

`0` all cases passed · `1` bad usage / malformed suite · `2` one or more
cases failed or were flaky (a result, not an error) · `3` model could not be
invoked · `4` a suite/report file was unreadable. Full taxonomy: SPEC.md §8.
