"""Drive the editor via CDP: toggle freehand, draw a stroke, report object count."""

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


for _ in range(50):
    if js("!!document.querySelector('canvas')"):
        break
    time.sleep(0.2)
time.sleep(2)

print("objects before:", js("document.querySelectorAll('.object-row').length"))
clicked = js(
    "(() => { const b=[...document.querySelectorAll('button')].find(x=>x.textContent.includes('自由绘制')); if(!b) return 'missing'; b.click(); return b.textContent; })()"
)
print("clicked:", clicked)
time.sleep(0.5)

rect = js(
    "(() => { const r=document.querySelector('canvas').getBoundingClientRect(); return {x:r.x,y:r.y,w:r.width,h:r.height}; })()"
)
print("canvas:", rect)
x0 = rect["x"] + rect["w"] * 0.25
y0 = rect["y"] + rect["h"] * 0.6

call(
    "Input.dispatchMouseEvent",
    {"type": "mousePressed", "x": x0, "y": y0, "button": "left", "clickCount": 1, "buttons": 1},
)
for step in range(1, 16):
    call(
        "Input.dispatchMouseEvent",
        {
            "type": "mouseMoved",
            "x": x0 + step * 12,
            "y": y0 - (step % 4) * 8,
            "button": "left",
            "buttons": 1,
        },
    )
    time.sleep(0.02)
call(
    "Input.dispatchMouseEvent",
    {"type": "mouseReleased", "x": x0 + 180, "y": y0, "button": "left", "clickCount": 1, "buttons": 0},
)
time.sleep(4)

print("objects after:", js("document.querySelectorAll('.object-row').length"))
print("status:", js("document.querySelector('.statusbar')?.innerText"))
print("notice:", js("document.querySelector('.hint')?.innerText"))
print("error:", js("document.querySelector('.banner.error')?.innerText || ''"))

shot = call("Page.captureScreenshot", {"format": "png"})
with open("artifacts/ui-draw.png", "wb") as handle:
    handle.write(base64.b64decode(shot["data"]))
print("screenshot bytes:", len(base64.b64decode(shot["data"])))
ws.close()
