"""Resolving and invoking the model binary. Subprocess only — never import it."""
import json
import os
import shutil
import subprocess
import sys
import time

from .errors import PromptlabError

DEFAULT_MODEL = "stubmodel.py"
TIMEOUT_S = 30


def resolve_model_path():
    """SPEC §2: PROMPTLAB_MODEL env var, default 'stubmodel.py'."""
    name = os.environ.get("PROMPTLAB_MODEL", DEFAULT_MODEL)
    if os.path.isfile(name):
        return os.path.abspath(name)
    found = shutil.which(name)
    if found:
        return found
    raise PromptlabError(
        "model_unavailable",
        f"model binary '{name}' not found (set PROMPTLAB_MODEL, or place it in the CWD / on PATH)",
        3,
    )


def _build_argv(model_path, prompt_file, input_arg, temperature, max_tokens, seed, call_index):
    argv = [sys.executable, model_path] if model_path.endswith(".py") else [model_path]
    argv += ["--prompt", prompt_file, "--input", input_arg]
    argv += ["--temperature", str(temperature)]
    argv += ["--max-tokens", str(max_tokens)]
    if seed is not None:
        argv += ["--seed", str(seed)]
    if call_index is not None:
        argv += ["--call-index", str(call_index)]
    return argv


def invoke(model_path, prompt_file, input_arg, temperature, max_tokens, seed=None, call_index=None):
    """Runs the model once. Returns (result_dict, wall_ms). Raises PromptlabError(3) on any failure."""
    argv = _build_argv(model_path, prompt_file, input_arg, temperature, max_tokens, seed, call_index)
    t0 = time.perf_counter()
    try:
        proc = subprocess.run(argv, capture_output=True, text=True, timeout=TIMEOUT_S)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise PromptlabError("model_unavailable", f"could not invoke model: {e}", 3)
    wall_ms = (time.perf_counter() - t0) * 1000

    if proc.returncode != 0:
        stderr = (proc.stderr or "").strip().splitlines()
        detail = stderr[-1] if stderr else f"exit code {proc.returncode}"
        raise PromptlabError("model_unavailable", f"model invocation failed: {detail}", 3)
    try:
        result = json.loads(proc.stdout.strip())
    except json.JSONDecodeError as e:
        raise PromptlabError("model_unavailable", f"model produced non-JSON stdout: {e}", 3)

    for key in ("output", "tokens_in", "tokens_out", "finish"):
        if key not in result:
            raise PromptlabError("model_unavailable", f"model output missing required field '{key}'", 3)
    return result, wall_ms
