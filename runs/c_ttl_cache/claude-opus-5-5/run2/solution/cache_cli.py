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
