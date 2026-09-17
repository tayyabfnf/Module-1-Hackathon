"""Five-second human summary of a report (MUST 7)."""


def human_summary(report):
    t = report["totals"]
    lines = [
        f"promptlab run: {report['suite']}  (prompt {report['prompt_hash']}, {report['runs']} run(s))",
        f"  pass {t['passed']}  fail {t['failed']}  flaky {t['flaky']}  / {t['cases']} cases",
        f"  tokens in={t['tokens_in']} out={t['tokens_out']}  wall={t['wall_ms']:.0f}ms",
    ]
    worst = sorted(
        [c for c in report["cases"] if c["status"] != "pass"],
        key=lambda c: c["pass_rate"],
    )[:5]
    if worst:
        lines.append("  worst offenders:")
        for c in worst:
            bad = [a["type"] for a in c["assertions"] if a["failed"] > 0]
            lines.append(f"    {c['id']}: {c['status']} (pass_rate={c['pass_rate']}) — failing: {', '.join(bad) or 'n/a'}")
    return "\n".join(lines)
