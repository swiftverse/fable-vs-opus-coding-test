```python
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
```

```python
# file: cache_cli.py
"""Command-line front end for TTLCache: reads commands from standard input."""

import argparse
import json
import os
import sys

from ttlcache import TTLCache


def execute(cache: TTLCache, tokens: list[str]) -> str:
    cmd = tokens[0].upper()
    args = tokens[1:]

    if cmd == "SET":
        if len(args) not in (2, 3):
            return "ERR wrong number of arguments for SET"
        ttl = None
        if len(args) == 3:
            try:
                ttl = float(args[2])
            except ValueError:
                return "ERR invalid ttl"
        try:
            cache.set(args[0], args[1], ttl)
        except ValueError:
            return "ERR invalid ttl"
        return "OK"

    if cmd == "GET":
        if len(args) != 1:
            return "ERR wrong number of arguments for GET"
        value = cache.get(args[0])
        return "(nil)" if value is None else value

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


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="TTL/LRU cache command shell")
    parser.add_argument("--maxsize", type=int, default=128)
    parser.add_argument("--ttl", type=float, default=60.0)
    ns = parser.parse_args(argv)  # exits with status 2 on unparseable values

    try:
        cache = TTLCache(ns.maxsize, ns.ttl)
    except ValueError as exc:
        parser.error(str(exc))  # exits with status 2

    try:
        for line in sys.stdin:
            tokens = line.split()
            if not tokens:
                continue
            print(execute(cache, tokens), flush=True)
    except BrokenPipeError:
        # Reader went away; avoid a second error when stdout is flushed at exit.
        try:
            os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        except (OSError, ValueError):
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

Where the spec left the behaviour open, I chose as follows:

- **`set` on an expired key:** the old entry is removed and counted as an expiration, then the key is inserted as new.
- **`delete` on an expired key:** the entry is removed and counted as an expiration, and `delete` returns False.
- **`len(cache)`:** it purges every expired entry first, so those count towards `expirations`.
- **TTL values:** `nan` and booleans are rejected; `inf` is accepted and means the entry never expires.
- **CLI output:** each response is flushed immediately so the tool works interactively or over a pipe.