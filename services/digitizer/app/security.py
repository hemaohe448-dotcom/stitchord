"""Small, dependency-free request guard: API key, optional rate limit, body cap."""

from __future__ import annotations

import hmac
import os
import threading
import time
from collections import defaultdict, deque

from fastapi import Request
from fastapi.responses import JSONResponse

MAX_BODY_BYTES = 20 * 1024 * 1024
_WINDOW_SECONDS = 60.0
_rate_buckets: dict[str, deque[float]] = defaultdict(deque)
_rate_lock = threading.Lock()


def reset_rate_limiter() -> None:
    with _rate_lock:
        _rate_buckets.clear()


def _rate_limited(client: str, limit: int) -> bool:
    now = time.monotonic()
    with _rate_lock:
        bucket = _rate_buckets[client]
        while bucket and now - bucket[0] > _WINDOW_SECONDS:
            bucket.popleft()
        if len(bucket) >= limit:
            return True
        bucket.append(now)
        return False


async def guard(request: Request):
    """Return a response to reject, or None to continue."""
    path = request.url.path
    if not path.startswith("/v1/"):
        return None

    api_key = os.environ.get("STITCHORD_API_KEY", "").strip()
    if api_key:
        provided = request.headers.get("x-api-key", "")
        if not hmac.compare_digest(provided, api_key):
            return JSONResponse({"detail": "invalid or missing API key"}, status_code=401)

    try:
        length = int(request.headers.get("content-length", "0"))
    except ValueError:
        length = 0
    if length > MAX_BODY_BYTES:
        return JSONResponse({"detail": "request body too large"}, status_code=413)

    try:
        limit = int(os.environ.get("STITCHORD_RATE_LIMIT", "0"))
    except ValueError:
        limit = 0
    if limit > 0:
        client = request.client.host if request.client else "unknown"
        if _rate_limited(client, limit):
            return JSONResponse(
                {"detail": "rate limit exceeded"},
                status_code=429,
                headers={"Retry-After": str(int(_WINDOW_SECONDS))},
            )
    return None
