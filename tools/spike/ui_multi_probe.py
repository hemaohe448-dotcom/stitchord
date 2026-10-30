"""CDP check: shift-click multi-select and duplicate all selected."""

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
time.sleep(6)
for _ in range(30):
    if js("document.querySelectorAll('.object-row').length >= 2"):
        break
    time.sleep(0.5)
time.sleep(2)

print("rows:", js("document.querySelectorAll('.object-row').length"))
print(
    "select two:",
    js(
        "(() => { const rows=[...document.querySelectorAll('.object-row')];"
        "rows[0].dispatchEvent(new MouseEvent('click',{bubbles:true}));"
        "rows[1].dispatchEvent(new MouseEvent('click',{bubbles:true,shiftKey:true}));"
        "return rows.length; })()"
    ),
)
time.sleep(0.5)
print("selected:", js("document.querySelectorAll('.object-row.is-selected').length"))
print("heading:", js("document.querySelector('.sidebar h2:nth-of-type(1)')?.innerText"))
print("hint:", js("[...document.querySelectorAll('.hint')].map(x=>x.innerText).join(' | ')"))
print(
    "duplicate:",
    js(
        "(() => { const b=[...document.querySelectorAll('button')].find(x=>x.textContent.trim()==='复制对象');"
        "if(!b) return 'missing'; b.click(); return 'clicked'; })()"
    ),
)
time.sleep(2)
print("rows after duplicate:", js("document.querySelectorAll('.object-row').length"))
print("selected after duplicate:", js("document.querySelectorAll('.object-row.is-selected').length"))

shot = call("Page.captureScreenshot", {"format": "png"})
with open("artifacts/ui-multi.png", "wb") as handle:
    handle.write(base64.b64decode(shot["data"]))
print("screenshot bytes:", len(base64.b64decode(shot["data"])))
ws.close()
