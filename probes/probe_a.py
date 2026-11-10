import time
import pytest
from free_slots import free_slots


@pytest.mark.parametrize("bad", ["\u0660\u0669:\u0660\u0660", "\uff10\uff19:00", "09:0\u0660"])
def test_non_ascii_digits_rejected(bad):
    with pytest.raises(ValueError):
        free_slots([], bad, "17:00")


def test_large_input_speed(record_property):
    busy = [(f"{(i // 60) % 24:02d}:{i % 60:02d}", f"{((i + 1) // 60) % 24:02d}:{(i + 1) % 60:02d}") for i in range(0, 1439, 2)] * 150
    t0 = time.perf_counter()
    res = free_slots(busy, "00:00", "24:00")
    dt = time.perf_counter() - t0
    record_property("seconds", round(dt, 4))
    assert len(res) == 720
