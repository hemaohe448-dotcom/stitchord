"""Fetch public documentation pages for parameter research (untrusted data).

Saves extracted text under .research/docs/ for offline reading. Not shipped.
"""

from __future__ import annotations

import hashlib
import os
import re
import sys
from html.parser import HTMLParser

import httpx

OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".research", "docs"))
os.makedirs(OUT, exist_ok=True)

URLS = [
    "https://inkstitch.org/docs/params/",
    "https://inkstitch.org/docs/stitch-library/",
    "https://inkstitch.org/docs/stitches/fill-stitch/",
    "https://inkstitch.org/docs/stitches/satin-column/",
    "https://inkstitch.org/docs/stitches/running-stitch/",
    "https://inkstitch.org/tutorials/underlay/",
    "https://inkstitch.org/tutorials/push-pull-compensation/",
    "https://docs.wilcom.com/embroiderystudio/28/en/OnlineHelp/Digitizing/properties/properties-9.htm",
    "https://docs.wilcom.com/embroiderystudio/26/en/OnlineHelp/Quality/PART_Quality/PART_Quality.htm",
]


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.skip = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in ("script", "style", "nav", "footer", "header"):
            self.skip += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style", "nav", "footer", "header") and self.skip:
            self.skip -= 1

    def handle_data(self, data: str) -> None:
        if not self.skip:
            line = " ".join(data.split())
            if line:
                self.parts.append(line)


def fetch(url: str) -> None:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", url.split("//", 1)[-1])[:80]
    try:
        response = httpx.get(
            url,
            timeout=40,
            follow_redirects=True,
            proxy="http://127.0.0.1:7890",
            headers={"User-Agent": "stitchord-research/0.1"},
        )
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL {url}: {exc}")
        return
    print(f"{response.status_code} {len(response.content)} {url}")
    if response.status_code != 200 or not response.content:
        return
    parser = TextExtractor()
    parser.feed(response.text)
    text = "\n".join(parser.parts)
    path = os.path.join(OUT, f"{slug}.txt")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(f"URL: {url}\nSHA256: {hashlib.sha256(response.content).hexdigest()}\n\n{text}")
    print("  ->", path, len(text))


if __name__ == "__main__":
    for item in URLS:
        fetch(item)
    sys.exit(0)
