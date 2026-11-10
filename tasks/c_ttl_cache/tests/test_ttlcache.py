import threading
import pytest
from ttlcache import TTLCache


class FakeClock:
    def __init__(self, t=1000.0):
        self.t = t

    def __call__(self):
        return self.t

    def advance(self, dt):
        self.t += dt


@pytest.fixture
def clock():
    return FakeClock()


def test_basic_set_get(clock):
    c = TTLCache(3, 10, clock=clock)
    c.set("a", 1)
    assert c.get("a") == 1
    assert c.get("missing") is None
    assert c.get("missing", "d") == "d"


def test_stats_keys_and_counts(clock):
    c = TTLCache(3, 10, clock=clock)
    c.set("a", 1)
    c.get("a")
    c.get("b")
    assert c.stats() == {"hits": 1, "misses": 1, "evictions": 0, "expirations": 0}


def test_stats_returns_copy(clock):
    c = TTLCache(3, 10, clock=clock)
    s = c.stats()
    s["hits"] = 99
    assert c.stats()["hits"] == 0


def test_expiry_boundary_is_inclusive(clock):
    c = TTLCache(3, 10, clock=clock)
    c.set("a", 1)
    clock.advance(9.999)
    assert c.get("a") == 1
    clock.advance(0.001)
    assert c.get("a") is None
    s = c.stats()
    assert s["expirations"] == 1 and s["misses"] == 1 and s["hits"] == 1


def test_per_entry_ttl_override(clock):
    c = TTLCache(3, 10, clock=clock)
    c.set("short", 1, ttl=1)
    c.set("long", 2)
    clock.advance(1)
    assert c.get("short") is None
    assert c.get("long") == 2


def test_lru_eviction_order(clock):
    c = TTLCache(2, 100, clock=clock)
    c.set("a", 1)
    c.set("b", 2)
    c.get("a")          # a is now most recent
    c.set("c", 3)       # evicts b
    assert "b" not in c
    assert c.get("a") == 1 and c.get("c") == 3
    assert c.stats()["evictions"] == 1


def test_set_existing_refreshes_recency_and_ttl_not_eviction(clock):
    c = TTLCache(2, 10, clock=clock)
    c.set("a", 1)
    c.set("b", 2)
    clock.advance(5)
    c.set("a", 11)      # refresh a; b is now LRU
    c.set("c", 3)       # evicts b
    assert "b" not in c
    clock.advance(6)    # a was refreshed at t+5, expires at t+15
    assert c.get("a") == 11
    assert c.stats()["evictions"] == 1


def test_expired_entries_removed_before_lru_eviction(clock):
    c = TTLCache(2, 10, clock=clock)
    c.set("old", 1, ttl=1)
    c.set("keep", 2)
    clock.advance(2)
    c.set("new", 3)
    assert c.get("keep") == 2 and c.get("new") == 3
    s = c.stats()
    assert s["evictions"] == 0 and s["expirations"] == 1


def test_contains_does_not_touch_stats_or_recency(clock):
    c = TTLCache(2, 10, clock=clock)
    c.set("a", 1)
    c.set("b", 2)
    assert "a" in c      # must NOT make a most recent
    c.set("c", 3)        # evicts a (LRU)
    assert "a" not in c
    s = c.stats()
    assert s["hits"] == 0 and s["misses"] == 0


def test_contains_false_for_expired(clock):
    c = TTLCache(2, 10, clock=clock)
    c.set("a", 1)
    clock.advance(10)
    assert "a" not in c


def test_len_counts_only_live(clock):
    c = TTLCache(5, 10, clock=clock)
    c.set("a", 1, ttl=1)
    c.set("b", 2)
    c.set("c", 3)
    assert len(c) == 3
    clock.advance(1)
    assert len(c) == 2
    assert c.stats()["expirations"] == 1


def test_delete(clock):
    c = TTLCache(5, 10, clock=clock)
    c.set("a", 1)
    assert c.delete("a") is True
    assert c.delete("a") is False
    c.set("b", 1)
    clock.advance(10)
    assert c.delete("b") is False


@pytest.mark.parametrize("maxsize,ttl", [(0, 1), (-1, 1), (1, 0), (1, -5), (1.5, 1)])
def test_constructor_validation(maxsize, ttl):
    with pytest.raises(ValueError):
        TTLCache(maxsize, ttl)


def test_set_ttl_validation(clock):
    c = TTLCache(2, 10, clock=clock)
    with pytest.raises(ValueError):
        c.set("a", 1, ttl=0)
    with pytest.raises(ValueError):
        c.set("a", 1, ttl=-1)


def test_none_and_falsy_values_are_stored(clock):
    c = TTLCache(3, 10, clock=clock)
    c.set("z", 0)
    c.set("n", None)
    assert c.get("z", "d") == 0
    assert c.get("n", "d") is None
    assert "n" in c
    assert c.stats()["hits"] == 2


def test_thread_safety_under_contention():
    c = TTLCache(50, 1000)
    errors = []
    gets_per_thread = 3000
    n_threads = 8

    def worker(i):
        try:
            for j in range(gets_per_thread):
                k = (i * 7 + j) % 120
                c.set(k, j)
                c.get((k + 3) % 120)
                len(c)
        except Exception as e:  # pragma: no cover
            errors.append(e)

    ts = [threading.Thread(target=worker, args=(i,)) for i in range(n_threads)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    assert not errors
    s = c.stats()
    assert s["hits"] + s["misses"] == gets_per_thread * n_threads
    assert len(c) <= 50
    # every new insert beyond capacity must be accounted for as an eviction
    assert s["evictions"] > 0
