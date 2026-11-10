# file: ttlcache.py
"""Thread-safe LRU cache with per-entry time-to-live (standard library only)."""

import math
import numbers
import threading
import time
from collections import OrderedDict

__all__ = ["TTLCache"]


def _check_ttl(ttl):
    # Rejects non-numbers, bools, NaN, zero and negatives.
    if (
        isinstance(ttl, bool)
        or not isinstance(ttl, numbers.Real)
        or not ttl > 0
    ):
        raise ValueError("ttl must be a number > 0")
    return ttl


class TTLCache:
    def __init__(self, maxsize: int, ttl: float, clock=time.monotonic):
        if isinstance(maxsize, bool) or not isinstance(maxsize, int) or maxsize < 1:
            raise ValueError("maxsize must be an int >= 1")
        self._maxsize = maxsize
        self._ttl = _check_ttl(ttl)
        self._clock = clock
        self._lock = threading.RLock()
        # key -> (value, expires_at); order: least recently used first.
        self._data = OrderedDict()
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._expirations = 0

    # -- internal helpers (call with the lock held) ---------------------

    def _purge_expired(self, now) -> None:
        dead = [k for k, (_, exp) in self._data.items() if now >= exp]
        for k in dead:
            del self._data[k]
        self._expirations += len(dead)

    # -- public API -------------------------------------------------------

    def set(self, key, value, ttl: float | None = None) -> None:
        ttl = self._ttl if ttl is None else _check_ttl(ttl)
        with self._lock:
            now = self._clock()
            try:
                expires = now + ttl
            except OverflowError:
                expires = math.inf

            entry = self._data.get(key)
            if entry is not None:
                if now >= entry[1]:
                    # Expired entry found: remove it, then treat as new insert.
                    del self._data[key]
                    self._expirations += 1
                else:
                    self._data[key] = (value, expires)
                    self._data.move_to_end(key)
                    return

            if len(self._data) >= self._maxsize:
                self._purge_expired(now)
                if len(self._data) >= self._maxsize:
                    self._data.popitem(last=False)
                    self._evictions += 1
            self._data[key] = (value, expires)

    def get(self, key, default=None):
        with self._lock:
            entry = self._data.get(key)
            if entry is None:
                self._misses += 1
                return default
            if self._clock() >= entry[1]:
                del self._data[key]
                self._expirations += 1
                self._misses += 1
                return default
            self._data.move_to_end(key)
            self._hits += 1
            return entry[0]

    def delete(self, key) -> bool:
        with self._lock:
            entry = self._data.get(key)
            if entry is None:
                return False
            del self._data[key]
            if self._clock() >= entry[1]:
                self._expirations += 1
                return False
            return True

    def __contains__(self, key) -> bool:
        with self._lock:
            entry = self._data.get(key)
            if entry is None:
                return False
            if self._clock() >= entry[1]:
                del self._data[key]
                self._expirations += 1
                return False
            return True

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
