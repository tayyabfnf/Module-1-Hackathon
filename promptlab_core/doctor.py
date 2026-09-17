"""doctor: environment diagnostic (MUST 18, SPEC §11)."""
import glob
import sys

from . import model as model_mod
from .assertions import DISPATCH
from .errors import PromptlabError


def run_doctor():
    checks = []
    ok = True

    py_ok = sys.version_info >= (3, 10)
    checks.append((py_ok, f"Python {sys.version.split()[0]} (>= 3.10 required)"))
    ok &= py_ok

    try:
        model_path = model_mod.resolve_model_path()
        result, _ = model_mod.invoke(model_path, _tmp_prompt(), "doctor check", 0.0, 16)
        model_ok = "output" in result
        checks.append((model_ok, f"model reachable and responding: {model_path}"))
    except PromptlabError as e:
        checks.append((False, f"model not reachable: {e.message}"))
        ok = False
    else:
        ok &= model_ok

    suites = sorted(glob.glob("suites/*.json"))
    checks.append((True, f"suites discoverable: {len(suites)} found under ./suites" if suites
                   else "suites discoverable: none found under ./suites (informational)"))

    assertion_ok = len(DISPATCH) == 8
    checks.append((assertion_ok, f"assertion types registered: {len(DISPATCH)}/8"))
    ok &= assertion_ok

    for passed, message in checks:
        print(f"  [{'ok' if passed else 'FAIL'}] {message}")
    return 0 if ok else 1


def _tmp_prompt():
    import atexit
    import os
    import tempfile
    fd, path = tempfile.mkstemp(suffix=".txt", prefix="promptlab_doctor_")
    with os.fdopen(fd, "w") as f:
        f.write("Respond with the word ok.")
    atexit.register(lambda: os.path.exists(path) and os.remove(path))
    return path
