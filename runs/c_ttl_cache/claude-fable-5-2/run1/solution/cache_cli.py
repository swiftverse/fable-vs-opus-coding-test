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
