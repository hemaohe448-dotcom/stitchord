from __future__ import annotations

import httpx

BASE = "https://api.github.com/repos/hemaohe448-dotcom/stitchord/actions"
PROXY = "http://127.0.0.1:7890"

for run in (41072227889, 41071709769):
    jobs = httpx.get(f"{BASE}/runs/{run}/jobs", proxy=PROXY, timeout=30).json()
    for job in jobs.get("jobs", []):
        print("=" * 60)
        print(run, job["name"], job["id"])
        response = httpx.get(
            f"{BASE}/jobs/{job['id']}/logs",
            proxy=PROXY,
            timeout=30,
            follow_redirects=True,
        )
        print("log status", response.status_code, "bytes", len(response.content))
        if response.status_code == 200:
            print(response.text[-3000:])
        else:
            print(response.text[:300])
