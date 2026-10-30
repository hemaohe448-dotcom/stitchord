"""Adapter: run a pinned Ink/Stitch checkout headlessly.

Only importable in the Python 3.11 worker image (Ink/Stitch + inkex + wxPython).
The 3.14 dev API keeps this module unimported until /v1/digitize is called.
"""

from __future__ import annotations

import hashlib
import os
import sys
import threading
import traceback
from dataclasses import dataclass
from pathlib import Path

from . import cache

def _repo_root_for(path: Path) -> Path:
    """Return the repo root, tolerating the shallow /app/app layout in Docker."""
    parents = path.resolve().parents
    return parents[3] if len(parents) > 3 else parents[-1]


_ADAPTER_PATH = Path(__file__).resolve()
_REPO_ROOT = _repo_root_for(_ADAPTER_PATH)
_import_checked = False
_import_ok = False
_last_import_error: str | None = None


@dataclass
class DigitizeResult:
    plan: dict
    dst: bytes
    sha256: str
    writer: str = "inkstitch"
    cached: bool = False
    groups_reused: int = 0


def _prepare_paths() -> None:
    defaults = {
        "STITCHORD_INKEX_PATH": _REPO_ROOT / ".research" / "repos" / "inkex",
        "STITCHORD_INKSTITCH_PATH": _REPO_ROOT / ".research" / "repos" / "inkstitch",
    }
    for key, default in defaults.items():
        path = Path(os.environ.get(key, str(default)))
        if path.exists() and str(path) not in sys.path:
            sys.path.insert(0, str(path))


def available() -> bool:
    """True when Ink/Stitch can be imported in this interpreter."""
    global _import_checked, _import_ok, _last_import_error
    if _import_checked:
        return _import_ok
    _import_checked = True
    try:
        _prepare_paths()
        import inkex  # noqa: F401
        from lib.elements import node_to_elements  # noqa: F401

        _import_ok = True
        _last_import_error = None
    except Exception as exc:  # noqa: BLE001 - optional capability
        _import_ok = False
        _last_import_error = f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}"
    return _import_ok


def import_error() -> str | None:
    return _last_import_error


def _plan_to_contract(plan, dpi: float = 96.0) -> dict:
    px_per_mm = dpi / 25.4
    blocks = []
    points = []
    for index, block in enumerate(plan):
        color_obj = getattr(block, "color", None)
        digits = getattr(color_obj, "hex_digits", None)
        color = f"#{digits.lower()}" if digits else "#000000"
        stitches = []
        for stitch in block:
            x_mm = round(stitch.x / px_per_mm, 3)
            y_mm = round(stitch.y / px_per_mm, 3)
            points.append((x_mm, y_mm))
            if getattr(stitch, "trim", False):
                command = "TRIM"
            elif getattr(stitch, "jump", False):
                command = "JUMP"
            elif getattr(stitch, "stop", False):
                command = "STOP"
            else:
                command = "STITCH"
            stitches.append({"x": x_mm, "y": y_mm, "command": command})
        blocks.append(
            {
                "id": f"cb-{index + 1}",
                "color": {"hex": color},
                "stitches": stitches,
            }
        )

    xs = [point[0] for point in points] or [0]
    ys = [point[1] for point in points] or [0]
    commands = [stitch["command"] for block in blocks for stitch in block["stitches"]]
    return {
        "schemaVersion": "1.0",
        "unit": "mm",
        "bounds": {
            "minX": min(xs),
            "minY": min(ys),
            "maxX": max(xs),
            "maxY": max(ys),
        },
        "colorBlocks": blocks,
        "stats": {
            "stitchCount": commands.count("STITCH"),
            "jumpCount": commands.count("JUMP"),
            "trimCount": commands.count("TRIM"),
            "colorChanges": max(0, len(blocks) - 1),
            "colorBlocks": len(blocks),
        },
    }


def _neutralize_thread_stop() -> None:
    """Ink/Stitch reads `current_thread().stop` and assumes it is an Event.

    Server/worker threads (anyio, pytest) may expose `.stop` as a bound method,
    which crashes `check_stop_flag()`. Shadow it with a real Event.
    """
    thread = threading.current_thread()
    stop = getattr(thread, "stop", None)
    if stop is not None and not (hasattr(stop, "is_set") and hasattr(stop, "set")):
        try:
            thread.stop = threading.Event()  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001 - best effort, only for incompatible threads
            pass


def digitize_svg(svg_path: Path, dst_path: Path, dpi: float = 96.0) -> DigitizeResult:
    _prepare_paths()
    _neutralize_thread_stop()

    import lib.utils.settings as settings

    settings.global_settings._settings["cache_size"] = 0

    import inkex
    from lib import output
    from lib.elements import node_to_elements
    from lib.stitch_plan.stitch_plan import stitch_groups_to_stitch_plan

    document = inkex.load_svg(str(svg_path))
    root = document.getroot()

    groups = []
    groups_reused = 0
    from lxml import etree

    context = "|".join(
        str(root.get(attribute, ""))
        for attribute in ("width", "height", "viewBox", "version")
    )

    for node in root.iter():
        if node is root or len(node) != 0:
            continue
        key = None
        try:
            key = hashlib.sha256(
                etree.tostring(node) + b"\0" + context.encode("utf-8")
            ).hexdigest()
        except Exception:  # noqa: BLE001 - cache is best-effort
            key = None
        if key:
            cached_groups = cache.get_groups(key)
            if cached_groups is not None:
                groups.extend(cached_groups)
                groups_reused += 1
                continue
        element_groups = []
        try:
            elements = node_to_elements(node)
        except Exception:  # noqa: BLE001 - unsupported leaf
            elements = []
        for element in elements:
            element_groups.extend(element.embroider(None))
        if key:
            cache.put_groups(key, element_groups)
        groups.extend(element_groups)
    if not groups:
        raise ValueError("no embroiderable elements found in SVG")

    plan = stitch_groups_to_stitch_plan(groups)
    contract = _plan_to_contract(plan, dpi=dpi)

    writer = "inkstitch"
    if dst_path.suffix.lower() == ".jef":
        # pystitch's JefWriter emits a file its own reader rejects (offset table);
        # fall back to pyembroidery's writer for this format only.
        from .convert import plan_to_pattern
        from .models import StitchPlan

        import pyembroidery

        pattern = plan_to_pattern(StitchPlan.model_validate(contract))
        pyembroidery.write_jef(pattern, str(dst_path))
        writer = "pyembroidery-fallback"
    else:
        output.write_embroidery_file(str(dst_path), plan, root, settings={"date": ""})

    payload = dst_path.read_bytes()
    return DigitizeResult(
        plan=contract,
        dst=payload,
        sha256=hashlib.sha256(payload).hexdigest(),
        writer=writer,
        groups_reused=groups_reused,
    )
