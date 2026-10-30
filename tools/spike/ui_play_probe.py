"""CDP check: stitch playback advances and can be paused."""

from __future__ import annotations

import base64
import json
import time

import httpx
from websockets.sync.client import connect

targets = httpx.get("http://127.0.0.1:9222/json", trust_env=False, timeout=10).json()
page = next(
    item
    for item in targets
    if item["type"] == "page" and "127.0.0.1:5173" in item["url"]
)
ws = connect(
    page["webSocketDebuggerUrl"],
    additional_headers={"Origin": "http://localhost"},
    max_size=50_000_000,
    legacy=True,
)
counter = 0


def call(method: str, params: dict | None = None) -> dict:
    global counter
    counter += 1
    ws.send(json.dumps({"id": counter, "method": method, "params": params or {}}))
    while True:
        message = json.loads(ws.recv())
        if message.get("id") == counter:
            if "error" in message:
                raise RuntimeError(message["error"])
            return message["result"]


def js(expression: str):
    result = call(
        "Runtime.evaluate",
        {"expression": expression, "returnByValue": True, "awaitPromise": True},
    )
    return result["result"].get("value")


call("Page.reload")
time.sleep(7)
for _ in range(20):
    if js("!!document.querySelector('.playback-count')"):
        break
    time.sleep(0.5)

print("before:", js("document.querySelector('.playback-count')?.innerText"))
print(
    "click:",
    js(
        "(() => { const b=[...document.querySelectorAll('button')].find(x=>x.textContent.trim()==='播放');"
        "if(!b) return 'missing'; b.click(); return 'ok'; })()"
    ),
)
time.sleep(2)
print("after 2s:", js("document.querySelector('.playback-count')?.innerText"))
print("button:", js("document.querySelector('.playback button')?.innerText"))
print(
    "pause:",
    js(
        "(() => { const b=document.querySelector('.playback button'); b?.click(); return b?.innerText; })()"
    ),
)
time.sleep(1)
print("paused at:", js("document.querySelector('.playback-count')?.innerText"))

shot = call("Page.captureScreenshot", {"format": "png"})
with open("artifacts/ui-playback.png", "wb") as handle:
    handle.write(base64.b64decode(shot["data"]))
print("screenshot bytes:", len(base64.b64decode(shot["data"])))
ws.close()
