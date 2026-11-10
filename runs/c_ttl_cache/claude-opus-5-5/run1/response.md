```python
# file: ttlcache.py
"""Thread-safe LRU cache with per-entry time-to-live."""

from __future__ import annotations

import numbers
import threading
import time
from collections import OrderedDict
from typing import Any, Callable

__all__ = ["TTLCache"]


def _valid_ttl(ttl: Any) -> bool:
    return (
        isinstance(ttl, numbers.Real)
        and not isinstance(ttl, bool)
        and ttl > 0  # NaN fails this comparison
    )


class TTLCache:
    """An LRU cache whose entries expire after a time-to-live.

    An entry set at time ``t`` with ttl ``x`` is live while ``clock() < t + x``
    and expired once ``clock() >= t + x``.
    """

    def __init__(
        self,
        maxsize: int,
        ttl: float,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if not isinstance(maxsize, int) or isinstance(maxsize, bool) or maxsize < 1:
            raise ValueError("maxsize must be an int >= 1")
        if not _valid_ttl(ttl):
            raise ValueError("ttl must be a number > 0")
        if not callable(clock):
            raise ValueError("clock must be callable")

        self._maxsize = maxsize
        self._ttl = ttl
        self._clock = clock
        # key -> (value, expires_at); order is LRU (first) -> MRU (last)
        self._data: OrderedDict[Any, tuple[Any, float]] = OrderedDict()
        self._lock = threading.RLock()
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._expirations = 0

    # ----- internal helpers (caller must hold the lock) -----

    def _expire_if_needed(self, key: Any, now: float) -> bool:
        """If ``key`` is present but expired, remove it.

        Returns True if the key is present and live afterwards.
        """
        entry = self._data.get(key)
        if entry is None:
            return False
        if now >= entry[1]:
            del self._data[key]
            self._expirations += 1
            return False
        return True

    def _purge_expired(self, now: float) -> None:
        expired = [k for k, (_, exp) in self._data.items() if now >= exp]
        for k in expired:
            del self._data[k]
        self._expirations += len(expired)

    # ----- public API -----

    def set(self, key: Any, value: Any, ttl: float | None = None) -> None:
        if ttl is None:
            ttl = self._ttl
        elif not _valid_ttl(ttl):
            raise ValueError("ttl must be a number > 0")

        with self._lock:
            now = self._clock()
            if self._expire_if_needed(key, now):
                # Live existing key: replace, reset expiry, mark MRU.
                self._data[key] = (value, now + ttl)
                self._data.move_to_end(key)
                return

            # Inserting a new key.
            if len(self._data) >= self._maxsize:
                self._purge_expired(now)
                if len(self._data) >= self._maxsize:
                    self._data.popitem(last=False)
                    self._evictions += 1
            self._data[key] = (value, now + ttl)

    def get(self, key: Any, default: Any = None) -> Any:
        with self._lock:
            now = self._clock()
            if self._expire_if_needed(key, now):
                self._data.move_to_end(key)
                self._hits += 1
                return self._data[key][0]
            self._misses += 1
            return default

    def delete(self, key: Any) -> bool:
        with self._lock:
            now = self._clock()
            if self._expire_if_needed(key, now):
                del self._data[key]
                return True
            return False

    def __contains__(self, key: Any) -> bool:
        with self._lock:
            return self._expire_if_needed(key, self._clock())

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

Reads commands from stdin, one per line, and prints one line per command.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from typing import TextIO

from ttlcache import TTLCache


def _positive_int(text: str) -> int:
    try:
        value = int(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"invalid int value: {text!r}")
    if value < 1:
        raise argparse.ArgumentTypeError("must be >= 1")
    return value


def _positive_float(text: str) -> float:
    try:
        value = float(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"invalid number: {text!r}")
    if math.isnan(value) or value <= 0:
        raise argparse.ArgumentTypeError("must be a number > 0")
    return value


def _parse_ttl(text: str) -> float | None:
    try:
        value = float(text)
    except ValueError:
        return None
    if math.isnan(value) or value <= 0:
        return None
    return value


def handle_line(cache: TTLCache, line: str) -> str | None:
    """Process one input line; return the output line, or None if blank."""
    tokens = line.split()
    if not tokens:
        return None
    cmd = tokens[0].upper()
    args = tokens[1:]

    if cmd == "SET":
        if len(args) not in (2, 3):
            return "ERR wrong number of arguments for SET"
        key, value = args[0], args[1]
        if len(args) == 3:
            ttl = _parse_ttl(args[2])
            if ttl is None:
                return "ERR invalid ttl"
            try:
                cache.set(key, value, ttl)
            except ValueError:
                return "ERR invalid ttl"
        else:
            cache.set(key, value)
        return "OK"

    if cmd == "GET":
        if len(args) != 1:
            return "ERR wrong number of arguments for GET"
        sentinel = object()
        value = cache.get(args[0], sentinel)
        return "(nil)" if value is sentinel else str(value)

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

    return f"ERR unknown command {tokens[0]!r}"


def run(cache: TTLCache, stdin: TextIO, stdout: TextIO) -> None:
    for line in stdin:
        out = handle_line(cache, line)
        if out is not None:
            stdout.write(out + "\n")
            stdout.flush()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Interactive LRU cache with per-entry TTL."
    )
    parser.add_argument("--maxsize", type=_positive_int, default=128,
                        help="maximum number of entries (default: 128)")
    parser.add_argument("--ttl", type=_positive_float, default=60.0,
                        help="default time-to-live in seconds (default: 60)")
    ns = parser.parse_args(argv)

    try:
        cache = TTLCache(ns.maxsize, ns.ttl)
    except ValueError as exc:
        parser.error(str(exc))  # exits with status 2

    try:
        run(cache, sys.stdin, sys.stdout)
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
```