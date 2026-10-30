"""Probe: which Ink/Stitch modules truly require wx at import time.

Run with PYTHONPATH pointing at inkex + inkstitch. On upstream Ink/Stitch this
is expected to FAIL for `lib.elements` (tartan -> wx); it documents the coupling
that made the "no-wx" idea unviable. Kept as evidence, not as a passing test.
"""

import sys


class WxBlocker:
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "wx" or fullname.startswith("wx."):
            raise ImportError(f"wx blocked for probe: {fullname}")
        return None


sys.meta_path.insert(0, WxBlocker())

try:
    from lib import output  # noqa: F401
    print("output: ok without wx")
except Exception as exc:  # noqa: BLE001
    print(f"output: FAILED without wx -> {type(exc).__name__}: {exc}")

try:
    from lib.elements import node_to_elements  # noqa: F401
    print("elements: ok without wx")
except Exception as exc:  # noqa: BLE001
    print(f"elements: FAILED without wx -> {type(exc).__name__}: {exc}")

try:
    from lib.stitch_plan.stitch_plan import stitch_groups_to_stitch_plan  # noqa: F401
    print("stitch_plan: ok without wx")
except Exception as exc:  # noqa: BLE001
    print(f"stitch_plan: FAILED without wx -> {type(exc).__name__}: {exc}")
