```python
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
```

```python
# file: cache_cli.py
"""Command-line front end for TTLCache. Reads commands from standard input."""

import argparse
import json
import os
import sys

from ttlcache import TTLCache


def handle(cache: TTLCache, tokens: list[str]) -> str:
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
            print(handle(cache, tokens), flush=True)
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

Both files are written as specified but have not been run or tested. In the places where the spec was silent, I made these choices:

- **`set` on an expired key:** the old entry is removed and counted as an expiration, and the call is then handled as a new insert, so rule 6 applies.
- **`delete` on an expired key:** the entry is removed, counted as an expiration, and the call returns `False`.
- **`len(cache)`:** it removes every expired entry it finds and counts each as an expiration.
- **Booleans:** `True`/`False` are rejected for `maxsize` and `ttl` with `ValueError`.
- **NaN and infinity:** a NaN ttl is rejected; `inf` is accepted and the entry never expires.
- **CLI values with spaces:** these aren't supported, since tokens are whitespace-separated; `SET k a b c` returns a wrong-number-of-arguments error.
- **Invalid `--maxsize`/`--ttl`:** the program exits with status 2 and prints a usage message to stderr.