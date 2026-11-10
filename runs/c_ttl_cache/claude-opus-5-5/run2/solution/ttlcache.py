# file: ttlcache.py
"""Thread-safe LRU cache with per-entry time-to-live (standard library only)."""

from __future__ import annotations

import numbers
import threading
import time
from collections import OrderedDict
from typing import Any, Callable

__all__ = ["TTLCache"]


def _is_number(value: Any) -> bool:
    return isinstance(value, numbers.Real) and not isinstance(value, bool)


def _validate_ttl(ttl: Any, name: str = "ttl") -> float:
    # "not ttl > 0" also rejects NaN.
    if not _is_number(ttl) or not ttl > 0:
        raise ValueError(f"{name} must be a number > 0, got {ttl!r}")
    return ttl


class TTLCache:
    """An LRU cache whose entries expire after a time-to-live.

    An entry set at time ``t`` with ttl ``x`` is live while ``clock() < t + x``
    and expired once ``clock() >= t + x``.
    """

    def __init__(self, maxsize: int, ttl: float, clock: Callable[[], float] = time.monotonic):
        if not isinstance(maxsize, int) or isinstance(maxsize, bool) or maxsize < 1:
            raise ValueError(f"maxsize must be an int >= 1, got {maxsize!r}")
        _validate_ttl(ttl)
        if not callable(clock):
            raise ValueError("clock must be a zero-argument callable")

        self._maxsize = maxsize
        self._ttl = ttl
        self._clock = clock
        # key -> (value, expires_at); order is LRU (first) to MRU (last).
        self._data: OrderedDict[Any, tuple[Any, float]] = OrderedDict()
        self._lock = threading.RLock()
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._expirations = 0

    # ----- internal helpers (caller must hold the lock) -----

    def _expire_if_needed(self, key: Any, now: float) -> bool:
        """Remove ``key`` if present and expired. Return True if it was removed."""
        entry = self._data.get(key)
        if entry is not None and now >= entry[1]:
            del self._data[key]
            self._expirations += 1
            return True
        return False

    def _purge_expired(self, now: float) -> None:
        expired = [k for k, (_, exp) in self._data.items() if now >= exp]
        for k in expired:
            del self._data[k]
        self._expirations += len(expired)

    # ----- public API -----

    def set(self, key: Any, value: Any, ttl: float | None = None) -> None:
        if ttl is None:
            ttl = self._ttl
        else:
            _validate_ttl(ttl)
        with self._lock:
            now = self._clock()
            expires_at = now + ttl
            self._expire_if_needed(key, now)
            if key in self._data:
                # Replacement: new value, new expiry, most recently used.
                self._data[key] = (value, expires_at)
                self._data.move_to_end(key)
                return
            if len(self._data) >= self._maxsize:
                self._purge_expired(now)
                if len(self._data) >= self._maxsize:
                    self._data.popitem(last=False)
                    self._evictions += 1
            self._data[key] = (value, expires_at)

    def get(self, key: Any, default: Any = None) -> Any:
        with self._lock:
            now = self._clock()
            if self._expire_if_needed(key, now) or key not in self._data:
                self._misses += 1
                return default
            self._data.move_to_end(key)
            self._hits += 1
            return self._data[key][0]

    def delete(self, key: Any) -> bool:
        with self._lock:
            now = self._clock()
            if self._expire_if_needed(key, now):
                return False
            if key in self._data:
                del self._data[key]
                return True
            return False

    def __contains__(self, key: Any) -> bool:
        with self._lock:
            now = self._clock()
            if self._expire_if_needed(key, now):
                return False
            return key in self._data

    def __len__(self) -> int:
        with self._lock:
            self._purge_expired(self._clock())
            return len(self._data)

    def stats(self) -> dict:
        with self._lock:
            return {
                "hits": self._hits,
                "misses": self._misses,
                "evictions": self._evictions,
                "expirations": self._expirations,
            }

    def __repr__(self) -> str:
        return f"{type(self).__name__}(maxsize={self._maxsize!r}, ttl={self._ttl!r})"
