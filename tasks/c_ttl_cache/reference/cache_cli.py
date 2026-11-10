# file: cache_cli.py
import argparse
import json
import sys

from ttlcache import TTLCache


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--maxsize", type=int, default=128)
    ap.add_argument("--ttl", type=float, default=60)
    a = ap.parse_args(argv)
    try:
        cache = TTLCache(a.maxsize, a.ttl)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    for line in sys.stdin:
        parts = line.split()
        if not parts:
            continue
        cmd, args = parts[0].upper(), parts[1:]
        try:
            if cmd == "SET" and len(args) in (2, 3):
                ttl = float(args[2]) if len(args) == 3 else None
                cache.set(args[0], args[1], ttl)
                out = "OK"
            elif cmd == "GET" and len(args) == 1:
                v = cache.get(args[0])
                out = "(nil)" if v is None else v
            elif cmd == "DEL" and len(args) == 1:
                out = "1" if cache.delete(args[0]) else "0"
            elif cmd == "LEN" and not args:
                out = str(len(cache))
            elif cmd == "STATS" and not args:
                out = json.dumps(cache.stats(), sort_keys=True)
            else:
                out = "ERR bad command"
        except ValueError as e:
            out = f"ERR {e}"
        print(out, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
