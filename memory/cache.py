"""LRU cache for recent extractions and classifications.

Keyed by document content hash.  Avoids re-processing identical
documents within the TTL window.
"""

from __future__ import annotations

import hashlib
from collections import OrderedDict
from datetime import datetime, timezone, timedelta
from typing import Any


class TTLCache:
    """Simple LRU + TTL cache."""

    def __init__(self, maxsize: int = 128, ttl_seconds: int = 3600) -> None:
        self._maxsize = maxsize
        self._ttl = timedelta(seconds=ttl_seconds)
        self._store: OrderedDict[str, tuple[Any, datetime]] = OrderedDict()

    def _content_hash(self, content: bytes | str) -> str:
        if isinstance(content, str):
            content = content.encode()
        return hashlib.sha256(content).hexdigest()

    def get(self, key: str) -> Any | None:
        if key not in self._store:
            return None
        value, timestamp = self._store[key]
        if datetime.now(timezone.utc) - timestamp > self._ttl:
            del self._store[key]
            return None
        self._store.move_to_end(key)
        return value

    def set(self, key: str, value: Any) -> None:
        if key in self._store:
            self._store.move_to_end(key)
        self._store[key] = (value, datetime.now(timezone.utc))
        if len(self._store) > self._maxsize:
            self._store.popitem(last=False)

    def clear(self) -> None:
        self._store.clear()


# Module-level singletons
classification_cache = TTLCache(maxsize=64, ttl_seconds=3600)
extraction_cache = TTLCache(maxsize=32, ttl_seconds=7200)
