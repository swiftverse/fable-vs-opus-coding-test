import math
import os
import subprocess
import sys
import time
import pytest
from ttlcache import TTLCache

HERE = os.environ.get("SOLUTION_DIR", os.getcwd())


def test_nan_ttl_rejected():
    with pytest.raises(ValueError):
        TTLCache(2, float("nan"))
    c = TTLCache(2, 10)
    with pytest.raises(ValueError):
        c.set("a", 1, ttl=float("nan"))


def test_cli_rejects_nan_ttl_and_extra_args():
    p = subprocess.run([sys.executable, os.path.join(HERE, "cache_cli.py")], input="SET a 1 nan\nSET a b c d\nLEN x\nGET a b\n",
                       capture_output=True, text=True, timeout=20, cwd=HERE)
    assert [l[:3] for l in p.stdout.splitlines()] == ["ERR"] * 4


def test_full_cache_insert_speed(record_property):
    # 5,000-entry cache, 50,000 distinct inserts: every insert after the first 5,000 hits the "full" path.
    c = TTLCache(5000, 1000)
    t0 = time.perf_counter()
    for i in range(50_000):
        c.set(i, i)
    dt = time.perf_counter() - t0
    record_property("seconds", round(dt, 4))
    assert len(c) == 5000 and c.stats()["evictions"] == 45_000


def test_mixed_ops_throughput(record_property):
    c = TTLCache(1000, 1000)
    t0 = time.perf_counter()
    for i in range(100_000):
        c.set(i % 1500, i)
        c.get((i * 7) % 1500)
    dt = time.perf_counter() - t0
    record_property("seconds", round(dt, 4))


def test_cli_throughput(record_property):
    cmds = "".join(f"SET k{i % 500} v{i}\nGET k{(i * 3) % 500}\n" for i in range(20_000))
    t0 = time.perf_counter()
    p = subprocess.run([sys.executable, os.path.join(HERE, "cache_cli.py")], input=cmds, capture_output=True, text=True, timeout=120, cwd=HERE)
    dt = time.perf_counter() - t0
    record_property("seconds", round(dt, 4))
    assert len(p.stdout.splitlines()) == 40_000
