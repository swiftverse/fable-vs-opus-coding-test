# file: ttlcache.py
"""Thread-safe LRU cache with per-entry time-to-live (standard library only)."""

import threading
import time
from collections import OrderedDict
from numbers import Real

__all__ = ["TTLCache"]


def _valid_ttl(ttl) -> bool:
    # Must be a real number > 0. bool is rejected; NaN fails the comparison.
    return isinstance(ttl, Real) and not isinstance(ttl, bool) and ttl > 0


class TTLCache:
    def __init__(self, maxsize: int, ttl: float, clock=time.monotonic):
        if not isinstance(maxsize, int) or isinstance(maxsize, bool) or maxsize < 1:
            raise ValueError("maxsize must be an int >= 1")
        if not _valid_ttl(ttl):
            raise ValueError("ttl must be a number > 0")
        if not callable(clock):
            raise TypeError("clock must be callable")
        self._maxsize = maxsize
        self._ttl = ttl
        self._clock = clock
        self._lock = threading.RLock()
        # key -> (value, expires_at); order: least recently used first.
        self._data: OrderedDict = OrderedDict()
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._expirations = 0

    # ---- internal helpers (must be called with the lock held) ----

    def _purge_expired(self, now) -> None:
        expired = [k for k, (_, exp) in self._data.items() if now >= exp]
        for k in expired:
            del self._data[k]
        self._expirations += len(expired)

    def _live_entry(self, key, now):
        """Return the (value, expires_at) entry if live; drop it if expired."""
        entry = self._data.get(key)
        if entry is None:
            return None
        if now >= entry[1]:
            del self._data[key]
            self._expirations += 1
            return None
        return entry

    # ---- public API ----

    def set(self, key, value, ttl: float | None = None) -> None:
        if ttl is None:
            ttl = self._ttl
        elif not _valid_ttl(ttl):
            raise ValueError("ttl must be a number > 0")
        with self._lock:
            now = self._clock()
            if self._live_entry(key, now) is not None:
                # Replace: new value, new expiry, most recently used.
                self._data[key] = (value, now + ttl)
                self._data.move_to_end(key)
                return
            # New key (or the previous entry had expired and was removed).
            if len(self._data) >= self._maxsize:
                self._purge_expired(now)
                if len(self._data) >= self._maxsize:
                    self._data.popitem(last=False)
                    self._evictions += 1
            self._data[key] = (value, now + ttl)

    def get(self, key, default=None):
        with self._lock:
            entry = self._live_entry(key, self._clock())
            if entry is None:
                self._misses += 1
                return default
            self._data.move_to_end(key)
            self._hits += 1
            return entry[0]

    def delete(self, key) -> bool:
        with self._lock:
            if self._live_entry(key, self._clock()) is None:
                return False
            del self._data[key]
            return True

    def __contains__(self, key) -> bool:
        with self._lock:
            return self._live_entry(key, self._clock()) is not None

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
