# file: free_slots.py
"""Compute free time windows within a working day."""

import re

_TIME_RE = re.compile(r"([0-9]{2}):([0-9]{2})")
_END_OF_DAY = 24 * 60


def _parse(value) -> int:
    """Convert an 'HH:MM' string to minutes since midnight, validating strictly."""
    if not isinstance(value, str):
        raise ValueError(f"time must be a string in HH:MM format, got {value!r}")
    match = _TIME_RE.fullmatch(value)
    if match is None:
        raise ValueError(f"invalid time format: {value!r}")
    hours, minutes = int(match.group(1)), int(match.group(2))
    if hours == 24 and minutes == 0:
        return _END_OF_DAY
    if hours > 23 or minutes > 59:
        raise ValueError(f"time out of range: {value!r}")
    return hours * 60 + minutes


def _format(total: int) -> str:
    return f"{total // 60:02d}:{total % 60:02d}"


def free_slots(busy, day_start, day_end, min_minutes=0) -> list[tuple[str, str]]:
    """Return the free windows in [day_start, day_end) not covered by `busy`.

    Only windows of positive length that last at least `min_minutes` minutes
    are returned, sorted by start time.
    """
    if isinstance(min_minutes, bool) or not isinstance(min_minutes, int):
        raise ValueError("min_minutes must be a non-negative integer")
    if min_minutes < 0:
        raise ValueError("min_minutes must be non-negative")

    start_day = _parse(day_start)
    end_day = _parse(day_end)
    if start_day >= end_day:
        raise ValueError("day_start must be strictly earlier than day_end")

    try:
        iterator = iter(busy)
    except TypeError:
        raise ValueError("busy must be an iterable of (start, end) pairs") from None

    intervals: list[tuple[int, int]] = []
    for item in iterator:
        if not isinstance(item, (tuple, list)) or len(item) != 2:
            raise ValueError(f"busy interval must be a 2-item tuple or list: {item!r}")
        start = _parse(item[0])
        end = _parse(item[1])
        if start >= end:
            raise ValueError(f"busy interval start must be before end: {item!r}")
        # Clip to the working day; skip intervals entirely outside it.
        start = max(start, start_day)
        end = min(end, end_day)
        if start < end:
            intervals.append((start, end))

    intervals.sort()

    result: list[tuple[str, str]] = []

    def emit(a: int, b: int) -> None:
        length = b - a
        if length > 0 and length >= min_minutes:
            result.append((_format(a), _format(b)))

    cursor = start_day
    for start, end in intervals:
        if start > cursor:
            emit(cursor, start)
        if end > cursor:
            cursor = end
    emit(cursor, end_day)

    return result
