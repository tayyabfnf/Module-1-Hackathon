#!/usr/bin/env python3
"""A minimal stand-in for stubmodel.py, used ONLY by promptlab's own unittest
suite. It follows the same CLI contract (same flags, same output shape, same
exit codes) so the harness's own tests don't depend on the real starter-kit
model. It is NOT used for prompts/classify_v1.txt -> classify_v2.txt work —
that requires the real stubmodel.py + data/tickets.json from the brief.
"""
import argparse
import json
import math
import random
import sys


def read_input(spec):
    if spec.startswith("@"):
        path = spec[1:]
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except OSError:
            print(f"fake_model: cannot read input file: {path}", file=sys.stderr)
            sys.exit(3)
    return spec


def classify(text):
    t = text.lower()
    if "invoice" in t or "charged" in t or "refund" in t:
        return "billing"
    if "password" in t or "login" in t or "account" in t:
        return "account"
    if "ship" in t or "deliver" in t or "package" in t:
        return "shipping"
    return "other"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--prompt", required=True)
    p.add_argument("--input", required=True)
    p.add_argument("--temperature", type=float, default=0.0)
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--max-tokens", type=int, default=256)
    p.add_argument("--call-index", type=int, default=0)
    try:
        args = p.parse_args()
    except SystemExit:
        sys.exit(2)

    try:
        with open(args.prompt, "r", encoding="utf-8") as f:
            prompt_text = f.read()
    except OSError:
        print(f"fake_model: cannot read prompt file: {args.prompt}", file=sys.stderr)
        sys.exit(3)

    input_text = read_input(args.input)

    if "REFUSE_ME" in input_text:
        output = "I can't help with that request."
        finish = "refusal"
    else:
        category = classify(input_text)
        body = json.dumps({"category": category})
        if args.temperature > 0:
            rng = random.Random(args.seed + args.call_index) if args.seed is not None else random.Random()
            if rng.random() < 0.5:
                body = "```json\n" + body + "\n```"
            if rng.random() < 0.3:
                body = "Sure, here you go: " + body
        output = body
        finish = "stop"

    tokens_out = math.ceil(len(output) / 4)
    if tokens_out > args.max_tokens:
        keep_chars = max(1, args.max_tokens * 4)
        output = output[:keep_chars]
        tokens_out = math.ceil(len(output) / 4)
        finish = "length"

    result = {
        "output": output,
        "tokens_in": math.ceil((len(prompt_text) + len(input_text)) / 4),
        "tokens_out": tokens_out,
        "finish": finish,
        "latency_ms": 1,
    }
    print(json.dumps(result))
    sys.exit(0)


if __name__ == "__main__":
    main()
