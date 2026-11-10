Build a small two-file Python 3.11+ feature using only the standard library: a thread-safe LRU cache with per-entry time-to-live, plus a command-line front end.

File 1: `ttlcache.py`

```python
class TTLCache:
    def __init__(self, maxsize: int, ttl: float, clock=time.monotonic): ...
    def set(self, key, value, ttl: float | None = None) -> None: ...
    def get(self, key, default=None): ...
    def delete(self, key) -> bool: ...
    def __contains__(self, key) -> bool: ...
    def __len__(self) -> int: ...
    def stats(self) -> dict: ...
```

Rules:

1. `maxsize` must be an int >= 1 and `ttl` must be a number > 0, otherwise raise `ValueError`. A per-call `ttl` passed to `set` overrides the default for that entry and must also be > 0 (else `ValueError`).
2. `clock` is a zero-argument callable returning the current time in seconds. All expiry decisions must use it (tests inject a fake clock).
3. An entry set at time `t` with ttl `x` is live while `clock() < t + x` and expired when `clock() >= t + x`.
4. `get` returns the value for a live key and marks it most recently used (hit). For a missing or expired key it returns `default` (miss). An expired entry found by any operation is removed at that moment.
5. `set` on an existing key replaces the value, resets its expiry from now, and marks it most recently used. It is not an eviction.
6. When `set` inserts a new key and the cache already holds `maxsize` entries, first remove all expired entries; if it is still full, evict the least recently used entry.
7. `delete` removes a key and returns True if a live entry was removed, else False.
8. `key in cache` is True only for live entries. It does not count as a hit or miss and does not change recency.
9. `len(cache)` returns the number of live entries.
10. `stats()` returns a new dict with exactly these int keys: `hits`, `misses`, `evictions` (LRU evictions only), `expirations` (number of expired entries removed, for any reason).
11. All public methods must be safe to call from multiple threads at once.

File 2: `cache_cli.py`

A CLI run as `python cache_cli.py [--maxsize N] [--ttl SECONDS]` (defaults: maxsize 128, ttl 60). It creates one `TTLCache` (real clock) and reads commands from standard input, one per line, until EOF. Tokens are separated by whitespace. Commands are case-insensitive; keys and values are case-sensitive. For each non-blank line it prints exactly one line to standard output:

- `SET key value` or `SET key value ttl` -> `OK`
- `GET key` -> the value, or `(nil)` if missing/expired
- `DEL key` -> `1` if removed, else `0`
- `LEN` -> the number of live entries
- `STATS` -> the stats dict as JSON with sorted keys, for example `{"evictions": 0, "expirations": 0, "hits": 1, "misses": 0}`
- Unknown command, wrong number of arguments, or an invalid ttl -> `ERR <short message>`; processing continues with the next line.

Blank lines are ignored. The process exits with status 0 at EOF. Invalid `--maxsize`/`--ttl` values should make the program exit with a non-zero status.

Reply with exactly two ```python fenced code blocks. The first line of the first block must be `# file: ttlcache.py` and the first line of the second must be `# file: cache_cli.py`. Do not include tests.
