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
