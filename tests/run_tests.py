"""Minimal test runner — used when pytest isn't available.
Discovers test_* functions in test_bridge.py and provides tmp_path."""
import inspect
import sys
import tempfile
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import tests.test_bridge as tb  # noqa: E402

passed = failed = 0
for name, fn in sorted(vars(tb).items()):
    if not name.startswith("test_") or not callable(fn):
        continue
    kwargs = {}
    if "tmp_path" in inspect.signature(fn).parameters:
        kwargs["tmp_path"] = Path(tempfile.mkdtemp())
    try:
        fn(**kwargs)
        print(f"PASS {name}")
        passed += 1
    except Exception:
        print(f"FAIL {name}")
        traceback.print_exc()
        failed += 1

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
