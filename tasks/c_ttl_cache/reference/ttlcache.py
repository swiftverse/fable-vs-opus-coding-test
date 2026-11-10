# file: ttlcache.py
import threading
import time
from collections import OrderedDict


def _check_ttl(ttl):
    if isinstance(ttl, bool) or not isinstance(ttl, (int, float)) or not ttl > 0:
        raise ValueError("ttl must be > 0")


class TTLCache:
    def __init__(self, maxsize, ttl, clock=time.monotonic):
        if isinstance(maxsize, bool) or not isinstance(maxsize, int) or maxsize < 1:
            raise ValueError("maxsize must be an int >= 1")
        _check_ttl(ttl)
        self._maxsize, self._ttl, self._clock = maxsize, ttl, clock
        self._data = OrderedDict()
        self._lock = threading.RLock()
        self._s = {"hits": 0, "misses": 0, "evictions": 0, "expirations": 0}

    def _live(self, key, now):
        item = self._data.get(key)
        if item is None:
            return None
        if now >= item[1]:
            del self._data[key]
            self._s["expirations"] += 1
            return None
        return item

    def _purge(self, now):
        for k in [k for k, (_, exp) in self._data.items() if now >= exp]:
            del self._data[k]
            self._s["expirations"] += 1

    def set(self, key, value, ttl=None):
        if ttl is None:
            ttl = self._ttl
        _check_ttl(ttl)
        with self._lock:
            now = self._clock()
            if key in self._data:
                self._data[key] = (value, now + ttl)
                self._data.move_to_end(key)
                return
            if len(self._data) >= self._maxsize:
                self._purge(now)
                if len(self._data) >= self._maxsize:
                    self._data.popitem(last=False)
                    self._s["evictions"] += 1
            self._data[key] = (value, now + ttl)

    def get(self, key, default=None):
        with self._lock:
            item = self._live(key, self._clock())
            if item is None:
                self._s["misses"] += 1
                return default
            self._data.move_to_end(key)
            self._s["hits"] += 1
            return item[0]

    def delete(self, key):
        with self._lock:
            if self._live(key, self._clock()) is None:
                return False
            del self._data[key]
            return True

    def __contains__(self, key):
        with self._lock:
            return self._live(key, self._clock()) is not None

    def __len__(self):
        with self._lock:
            self._purge(self._clock())
            return len(self._data)

    def stats(self):
        with self._lock:
            return dict(self._s)
