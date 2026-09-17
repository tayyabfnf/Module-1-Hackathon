"""Entry point: promptlab run|compare|doctor."""
import argparse
import json
import sys

from . import compare as compare_mod
from . import runner
from . import suite as suite_mod
from .doctor import run_doctor
from .errors import PromptlabError
from .reporter import human_summary


def build_parser():
    p = argparse.ArgumentParser(prog="promptlab")
    sub = p.add_subparsers(dest="command", required=True)

    r = sub.add_parser("run")
    r.add_argument("--suite", required=True)
    r.add_argument("--runs", type=int, default=None)
    r.add_argument("--out", default=None)
    r.add_argument("--report", action="store_true")

    c = sub.add_parser("compare")
    c.add_argument("--baseline", required=True)
    c.add_argument("--candidate", required=True)
    c.add_argument("--out", default=None)

    sub.add_parser("doctor")
    return p


def _cmd_run(args):
    if args.runs is not None and args.runs < 1:
        raise PromptlabError("usage", "--runs must be a positive integer", 1)
    suite, suite_dir = suite_mod.load_suite(args.suite)
    report, exit_code = runner.run_suite(suite, suite_dir, runs_override=args.runs)

    text = json.dumps(report, indent=2)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text + "\n")
    else:
        print(text)
    if args.report:
        print(human_summary(report), file=sys.stderr)
    return exit_code


def _cmd_compare(args):
    baseline = compare_mod.load_report(args.baseline)
    candidate = compare_mod.load_report(args.candidate)
    diff = compare_mod.compare(baseline, candidate)

    text = json.dumps(diff, indent=2)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text + "\n")
    else:
        print(text)
    print(compare_mod.human_summary(diff), file=sys.stderr)
    return 2 if diff["summary"]["regressed"] > 0 else 0


def main(argv=None):
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        return e.code if isinstance(e.code, int) else 1

    try:
        if args.command == "run":
            return _cmd_run(args)
        if args.command == "compare":
            return _cmd_compare(args)
        if args.command == "doctor":
            return run_doctor()
    except PromptlabError as e:
        print(str(e), file=sys.stderr)
        return e.exit_code
    except Exception as e:  # noqa: BLE001 — MUST 9: no crash reaches the user
        print(f"promptlab: internal_error: {e}", file=sys.stderr)
        return 1
    return 1


if __name__ == "__main__":
    sys.exit(main())
