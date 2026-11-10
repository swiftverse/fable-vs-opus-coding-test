```python
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
```

```python
# file: cache_cli.py
"""Command-line front end for TTLCache.

Usage: python cache_cli.py [--maxsize N] [--ttl SECONDS]
Reads commands from standard input, one per line, until EOF.
"""

from __future__ import annotations

import argparse
import json
import sys

from ttlcache import TTLCache


def _parse_args(argv: list[str] | None) -> tuple[argparse.ArgumentParser, argparse.Namespace]:
    parser = argparse.ArgumentParser(description="Interactive TTL LRU cache.")
    parser.add_argument("--maxsize", type=int, default=128,
                        help="maximum number of entries (int >= 1, default 128)")
    parser.add_argument("--ttl", type=float, default=60.0,
                        help="default time-to-live in seconds (> 0, default 60)")
    return parser, parser.parse_args(argv)


def handle_line(cache: TTLCache, line: str) -> str | None:
    """Process one input line. Return the output line, or None for blank lines."""
    tokens = line.split()
    if not tokens:
        return None
    cmd, args = tokens[0].upper(), tokens[1:]

    if cmd == "SET":
        if len(args) not in (2, 3):
            return "ERR wrong number of arguments for SET"
        key, value = args[0], args[1]
        ttl = None
        if len(args) == 3:
            try:
                ttl = float(args[2])
            except ValueError:
                return "ERR invalid ttl"
        try:
            cache.set(key, value, ttl)
        except ValueError:
            return "ERR invalid ttl"
        return "OK"

    if cmd == "GET":
        if len(args) != 1:
            return "ERR wrong number of arguments for GET"
        value = cache.get(args[0])
        return "(nil)" if value is None else str(value)

    if cmd == "DEL":
        if len(args) != 1:
            return "ERR wrong number of arguments for DEL"
        return "1" if cache.delete(args[0]) else "0"

    if cmd == "LEN":
        if args:
            return "ERR wrong number of arguments for LEN"
        return str(len(cache))

    if cmd == "STATS":
        if args:
            return "ERR wrong number of arguments for STATS"
        return json.dumps(cache.stats(), sort_keys=True)

    return "ERR unknown command"


def main(argv: list[str] | None = None) -> int:
    parser, args = _parse_args(argv)
    try:
        cache = TTLCache(args.maxsize, args.ttl)
    except ValueError as exc:
        parser.error(str(exc))  # exits with status 2

    for line in sys.stdin:
        out = handle_line(cache, line)
        if out is not None:
            print(out, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```