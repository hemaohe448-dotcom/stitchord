from __future__ import annotations

import re

import httpx

for url in (
    "http://archive.ubuntu.com/ubuntu/pool/main/libj/libjpeg-turbo/",
    "http://archive.ubuntu.com/ubuntu/pool/main/t/tiff/",
):
    text = httpx.get(url, proxy="http://127.0.0.1:7890", timeout=30).text
    files = re.findall(r'href="([^"]+amd64\.deb)"', text)
    wanted = [
        name
        for name in files
        if name.startswith("libjpeg-turbo8_") or name.startswith("libtiff5_")
    ]
    print(url)
    print(wanted[-6:])
