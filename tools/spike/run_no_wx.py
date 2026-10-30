"""Run the Ink/Stitch spike while blocking every wx import.

Proves the headless path does not need wxPython once lib/tartan/palette.py is
patched to import wx lazily (patches/inkstitch/0001-lazy-wx.patch).
"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path


class WxBlocker:
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "wx" or fullname.startswith("wx."):
            raise ImportError(f"wx blocked for headless test: {fullname}")
        return None


sys.meta_path.insert(0, WxBlocker())
script = Path(__file__).with_name("inkstitch_headless_v2.py")
runpy.run_path(str(script), run_name="__main__")
