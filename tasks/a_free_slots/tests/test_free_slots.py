import copy
import pytest
from free_slots import free_slots


def test_example_from_spec():
    busy = [("10:00", "11:00"), ("09:30", "10:15"), ("13:00", "13:30")]
    assert free_slots(busy, "09:00", "17:00", 30) == [("09:00", "09:30"), ("11:00", "13:00"), ("13:30", "17:00")]


def test_no_busy_returns_whole_day():
    assert free_slots([], "09:00", "17:00") == [("09:00", "17:00")]


def test_fully_booked_returns_empty():
    assert free_slots([("08:00", "18:00")], "09:00", "17:00") == []


def test_touching_intervals_leave_no_gap():
    assert free_slots([("09:00", "10:00"), ("10:00", "11:00")], "09:00", "12:00") == [("11:00", "12:00")]


def test_unsorted_and_nested_overlaps():
    busy = [("14:00", "15:00"), ("09:00", "12:00"), ("10:00", "11:00"), ("11:30", "12:30")]
    assert free_slots(busy, "09:00", "17:00") == [("12:30", "14:00"), ("15:00", "17:00")]


def test_clips_intervals_partly_outside_day():
    busy = [("07:00", "09:30"), ("16:30", "19:00")]
    assert free_slots(busy, "09:00", "17:00") == [("09:30", "16:30")]


def test_ignores_intervals_entirely_outside_day():
    busy = [("06:00", "07:00"), ("18:00", "19:00"), ("17:00", "18:00")]
    assert free_slots(busy, "09:00", "17:00") == [("09:00", "17:00")]


def test_min_minutes_filters_short_gaps_inclusive():
    busy = [("09:00", "09:45"), ("10:15", "10:44"), ("11:14", "12:00")]
    # gaps: 09:45-10:15 (30), 10:44-11:14 (30), 12:00-13:00 (60)
    assert free_slots(busy, "09:00", "13:00", 30) == [("09:45", "10:15"), ("10:44", "11:14"), ("12:00", "13:00")]
    assert free_slots(busy, "09:00", "13:00", 31) == [("12:00", "13:00")]


def test_zero_length_gaps_never_returned():
    assert free_slots([("09:00", "10:00"), ("10:00", "17:00")], "09:00", "17:00", 0) == []


def test_end_of_day_24_00():
    assert free_slots([("00:00", "08:00"), ("22:00", "24:00")], "00:00", "24:00") == [("08:00", "22:00")]
    assert free_slots([("00:00", "23:00")], "00:00", "24:00") == [("23:00", "24:00")]


def test_accepts_lists_and_generators():
    gen = (x for x in [["10:00", "11:00"]])
    assert free_slots(gen, "09:00", "12:00") == [("09:00", "10:00"), ("11:00", "12:00")]


def test_output_is_zero_padded_tuples():
    res = free_slots([("01:05", "02:07")], "00:00", "03:00")
    assert res == [("00:00", "01:05"), ("02:07", "03:00")]
    assert all(isinstance(x, tuple) for x in res)


def test_does_not_mutate_input():
    busy = [["11:00", "12:00"], ["09:00", "10:00"]]
    snapshot = copy.deepcopy(busy)
    free_slots(busy, "08:00", "13:00")
    assert busy == snapshot


@pytest.mark.parametrize("bad", ["9:00", "12:60", "25:00", "24:01", "ab:cd", "", "0900", "09:00:00", None, 900, " 09:00"])
def test_invalid_time_strings_raise(bad):
    with pytest.raises(ValueError):
        free_slots([], bad, "17:00")


def test_invalid_busy_time_raises():
    with pytest.raises(ValueError):
        free_slots([("10:00", "10:75")], "09:00", "17:00")


def test_busy_start_not_before_end_raises():
    with pytest.raises(ValueError):
        free_slots([("11:00", "10:00")], "09:00", "17:00")
    with pytest.raises(ValueError):
        free_slots([("10:00", "10:00")], "09:00", "17:00")


def test_busy_start_not_before_end_raises_even_outside_day():
    with pytest.raises(ValueError):
        free_slots([("20:00", "19:00")], "09:00", "17:00")


def test_day_start_not_before_end_raises():
    with pytest.raises(ValueError):
        free_slots([], "17:00", "09:00")
    with pytest.raises(ValueError):
        free_slots([], "09:00", "09:00")


def test_negative_min_minutes_raises():
    with pytest.raises(ValueError):
        free_slots([], "09:00", "17:00", -1)
