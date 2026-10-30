from __future__ import annotations

import time

import httpx

RUN = 41084822203
URL = f"https://api.github.com/repos/hemaohe448-dotcom/stitchord/actions/runs/{RUN}"

for _ in range(80):
    data = httpx.get(URL, proxy="http://127.0.0.1:7890", timeout=30).json()
    print(time.strftime("%H:%M:%S"), data["status"], data.get("conclusion"), flush=True)
    if data["status"] == "completed":
        print("RESULT", data.get("conclusion"), flush=True)
        break
    time.sleep(30)
