```python
# file: free_slots.py
"""Compute free time windows within a working day, given busy intervals."""

from __future__ import annotations

from collections.abc import Iterable

__all__ = ["free_slots"]

_DIGITS = frozenset("0123456789")
_END_OF_DAY = 24 * 60


def _parse_time(value: object) -> int:
    """Parse a strict "HH:MM" string into minutes since midnight.

    Accepts "00:00" through "23:59" and the special value "24:00".
    Raises ValueError for anything else, including non-string values.
    """
    if not isinstance(value, str):
        raise ValueError(f"time must be a string in 'HH:MM' format, got {value!r}")
    if len(value) != 5 or value[2] != ":":
        raise ValueError(f"invalid time format: {value!r}")
    hh, mm = value[:2], value[3:]
    if not (set(hh) <= _DIGITS and set(mm) <= _DIGITS):
        raise ValueError(f"invalid time format: {value!r}")
    hours, minutes = int(hh), int(mm)
    if hours == 24 and minutes == 0:
        return _END_OF_DAY
    if hours > 23 or minutes > 59:
        raise ValueError(f"time out of range: {value!r}")
    return hours * 60 + minutes


def _format_time(total_minutes: int) -> str:
    """Format minutes since midnight as zero-padded "HH:MM"."""
    hours, minutes = divmod(total_minutes, 60)
    return f"{hours:02d}:{minutes:02d}"


def free_slots(
    busy: Iterable,
    day_start: str,
    day_end: str,
    min_minutes: int = 0,
) -> list[tuple[str, str]]:
    """Return the free windows within [day_start, day_end) not covered by busy intervals.

    Busy intervals are half-open [start, end). Only free windows of length
    >= min_minutes (and never zero-length) are returned, sorted by start.
    """
    # Validate min_minutes.
    if isinstance(min_minutes, bool) or not isinstance(min_minutes, int):
        raise ValueError(f"min_minutes must be a non-negative integer, got {min_minutes!r}")
    if min_minutes < 0:
        raise ValueError(f"min_minutes must be non-negative, got {min_minutes!r}")

    # Validate day bounds.
    start_of_day = _parse_time(day_start)
    end_of_day = _parse_time(day_end)
    if start_of_day >= end_of_day:
        raise ValueError(
            f"day_start must be strictly earlier than day_end: {day_start!r} >= {day_end!r}"
        )

    # Validate and clip busy intervals (without mutating input).
    if busy is None:
        raise ValueError("busy must be an iterable of (start, end) pairs")
    try:
        iterator = iter(busy)
    except TypeError:
        raise ValueError("busy must be an iterable of (start, end) pairs") from None

    clipped: list[tuple[int, int]] = []
    for item in iterator:
        if not isinstance(item, (tuple, list)) or len(item) != 2:
            raise ValueError(f"each busy interval must be a 2-item tuple or list, got {item!r}")
        b_start = _parse_time(item[0])
        b_end = _parse_time(item[1])
        if b_start >= b_end:
            raise ValueError(f"busy interval start must be earlier than end: {item!r}")
        lo = max(b_start, start_of_day)
        hi = min(b_end, end_of_day)
        if lo < hi:
            clipped.append((lo, hi))

    clipped.sort()

    # Sweep to find gaps.
    result: list[tuple[str, str]] = []
    threshold = max(min_minutes, 1)  # zero-length windows are never returned
    cursor = start_of_day
    for lo, hi in clipped:
        if lo > cursor and lo - cursor >= threshold:
            result.append((_format_time(cursor), _format_time(lo)))
        if hi > cursor:
            cursor = hi
    if end_of_day > cursor and end_of_day - cursor >= threshold:
        result.append((_format_time(cursor), _format_time(end_of_day)))

    return result
```