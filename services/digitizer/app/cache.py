"""Small bounded in-process cache for deterministic digitize results."""

from __future__ import annotations

import hashlib
import threading
from collections import OrderedDict

from .inkstitch_adapter import DigitizeResult

_MAX_ENTRIES = 32
_cache: OrderedDict[str, DigitizeResult] = OrderedDict()
_lock = threading.Lock()

_MAX_GROUP_ENTRIES = 256
_group_cache: OrderedDict[str, list] = OrderedDict()
_group_lock = threading.Lock()


def key_for(document, suffix: str) -> str:
    payload = document.model_dump_json(by_alias=True).encode("utf-8")
    return hashlib.sha256(payload + b"\0" + suffix.encode("ascii")).hexdigest()


def get(key: str) -> DigitizeResult | None:
    with _lock:
        result = _cache.get(key)
        if result is None:
            return None
        _cache.move_to_end(key)
        return result


def put(key: str, result: DigitizeResult) -> None:
    with _lock:
        _cache[key] = result
        _cache.move_to_end(key)
        while len(_cache) > _MAX_ENTRIES:
            _cache.popitem(last=False)


def clear() -> None:
    with _lock:
        _cache.clear()


def get_groups(key: str):
    with _group_lock:
        groups = _group_cache.get(key)
        if groups is None:
            return None
        _group_cache.move_to_end(key)
        return groups


def put_groups(key: str, groups: list) -> None:
    with _group_lock:
        _group_cache[key] = groups
        _group_cache.move_to_end(key)
        while len(_group_cache) > _MAX_GROUP_ENTRIES:
            _group_cache.popitem(last=False)


def clear_groups() -> None:
    with _group_lock:
        _group_cache.clear()
