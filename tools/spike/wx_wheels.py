from __future__ import annotations

import re

import httpx

for version in ("24.04", "22.04", "20.04"):
    url = (
        "https://extras.wxpython.org/wxPython4/extras/linux/gtk3/"
        f"ubuntu-{version}/"
    )
    try:
        text = httpx.get(url, proxy="http://127.0.0.1:7890", timeout=30).text
    except Exception as exc:
        print(version, type(exc).__name__, exc)
        continue
    wheels = re.findall(r'href="([^"]+\.whl)"', text)
    matches = [name for name in wheels if "cp311" in name]
    print(version, "cp311", matches[-5:])
    print(version, "cp312-4.2.5", [name for name in wheels if "cp312" in name and "4.2.5" in name])
