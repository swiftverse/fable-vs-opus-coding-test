```python
# file: free_slots.py
"""Compute free time windows in a working day given busy intervals."""

_DIGITS = frozenset("0123456789")
_END_OF_DAY = 24 * 60


def _parse(value) -> int:
    """Convert an 'HH:MM' string to minutes since midnight, validating strictly."""
    if not isinstance(value, str):
        raise ValueError(f"time must be a string in HH:MM format, got {value!r}")
    if (
        len(value) != 5
        or value[2] != ":"
        or value[0] not in _DIGITS
        or value[1] not in _DIGITS
        or value[3] not in _DIGITS
        or value[4] not in _DIGITS
    ):
        raise ValueError(f"invalid time format: {value!r}")
    hours = int(value[:2])
    minutes = int(value[3:])
    if hours == 24 and minutes == 0:
        return _END_OF_DAY
    if hours > 23 or minutes > 59:
        raise ValueError(f"time out of range: {value!r}")
    return hours * 60 + minutes


def _format(total: int) -> str:
    """Convert minutes since midnight to a zero-padded 'HH:MM' string."""
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

    start_of_day = _parse(day_start)
    end_of_day = _parse(day_end)
    if start_of_day >= end_of_day:
        raise ValueError("day_start must be strictly earlier than day_end")

    try:
        iterator = iter(busy)
    except TypeError:
        raise ValueError("busy must be an iterable of (start, end) pairs") from None

    clipped: list[tuple[int, int]] = []
    for item in iterator:
        if not isinstance(item, (tuple, list)) or len(item) != 2:
            raise ValueError(f"busy interval must be a 2-item tuple or list: {item!r}")
        start = _parse(item[0])
        end = _parse(item[1])
        if start >= end:
            raise ValueError(f"busy interval start must be before end: {item!r}")
        # Clip to the working day; drop intervals entirely outside it.
        start = max(start, start_of_day)
        end = min(end, end_of_day)
        if start < end:
            clipped.append((start, end))

    clipped.sort()

    result: list[tuple[str, str]] = []

    def emit(a: int, b: int) -> None:
        length = b - a
        if length > 0 and length >= min_minutes:
            result.append((_format(a), _format(b)))

    cursor = start_of_day
    for start, end in clipped:
        if start > cursor:
            emit(cursor, start)
        if end > cursor:
            cursor = end
    emit(cursor, end_of_day)

    return result
```