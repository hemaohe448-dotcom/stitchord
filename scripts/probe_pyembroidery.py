import pyembroidery
import inspect
import os
import tempfile

try:
    from importlib.metadata import version as _v
    print("version:", _v("pyembroidery"))
except Exception as exc:  # pragma: no cover
    print("version: unknown", exc)
for n in ["STITCH", "JUMP", "TRIM", "COLOR_CHANGE", "STOP", "END", "NEEDLE_AT"]:
    print(n, getattr(pyembroidery, n, "MISSING"))
p = pyembroidery.EmbPattern()
print("methods:", [m for m in ("add_stitch_absolute", "stitch_abs", "add_thread", "color_change", "trim", "end") if hasattr(p, m)])
print("write_dst sig:", inspect.signature(pyembroidery.write_dst))
print("read sig:", inspect.signature(pyembroidery.read))
d = r"D:\stitchord\.tmp"
os.makedirs(d, exist_ok=True)
path = os.path.join(d, "t.dst")
p.add_thread({"color": "#ff0000", "name": "red"})
p.stitch_abs(0, 0)
p.stitch_abs(100, 0)
p.stitch_abs(100, 50)
p.color_change()
p.stitch_abs(200, 0)
p.end()
pyembroidery.write_dst(p, path)
q = pyembroidery.read(path)
print("stitches:", q.stitches[:12])
print("threads:", q.threadlist)
print("bounds:", q.bounds())
print("size bytes:", os.path.getsize(path))
q2 = pyembroidery.read(path)
print("count read:", len(q2.stitches))
