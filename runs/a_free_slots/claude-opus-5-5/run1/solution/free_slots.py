# file: free_slots.py
"""Compute free time windows within a working day, given busy intervals."""

from __future__ import annotations

_DIGITS = frozenset("0123456789")


def _parse_time(value) -> int:
    """Parse a strict "HH:MM" string into minutes since midnight.

    Accepts "00:00" through "23:59", plus "24:00". Raises ValueError otherwise.
    """
    if not isinstance(value, str):
        raise ValueError(f"time must be a string in 'HH:MM' format, got {value!r}")
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
        return 24 * 60
    if not (0 <= hours <= 23) or not (0 <= minutes <= 59):
        raise ValueError(f"time out of range: {value!r}")
    return hours * 60 + minutes


def _format_time(total_minutes: int) -> str:
    """Format minutes since midnight as a zero-padded "HH:MM" string."""
    hours, minutes = divmod(total_minutes, 60)
    return f"{hours:02d}:{minutes:02d}"


def free_slots(busy, day_start, day_end, min_minutes=0) -> list[tuple[str, str]]:
    """Return free windows within [day_start, day_end) not covered by busy intervals.

    Args:
        busy: Iterable of 2-item tuples/lists (start, end) of "HH:MM" strings,
            each interpreted as the half-open interval [start, end).
        day_start: Start of the working day ("HH:MM").
        day_end: End of the working day ("HH:MM"; "24:00" allowed).
        min_minutes: Minimum length (in minutes) of returned windows; must be a
            non-negative integer.

    Returns:
        A list of (start, end) tuples of "HH:MM" strings, sorted by start.

    Raises:
        ValueError: On any invalid input as described in the specification.
    """
    # Validate min_minutes.
    if isinstance(min_minutes, bool) or not isinstance(min_minutes, int):
        raise ValueError(f"min_minutes must be a non-negative integer, got {min_minutes!r}")
    if min_minutes < 0:
        raise ValueError(f"min_minutes must be non-negative, got {min_minutes!r}")

    # Validate the day bounds.
    start_of_day = _parse_time(day_start)
    end_of_day = _parse_time(day_end)
    if start_of_day >= end_of_day:
        raise ValueError(
            f"day_start ({day_start!r}) must be strictly earlier than day_end ({day_end!r})"
        )

    # Validate and parse busy intervals without mutating the input.
    try:
        items = list(busy)
    except TypeError as exc:
        raise ValueError("busy must be an iterable of (start, end) pairs") from exc

    clipped: list[tuple[int, int]] = []
    for item in items:
        if not isinstance(item, (tuple, list)) or len(item) != 2:
            raise ValueError(f"busy interval must be a 2-item tuple or list, got {item!r}")
        b_start = _parse_time(item[0])
        b_end = _parse_time(item[1])
        if b_start >= b_end:
            raise ValueError(f"busy interval start must be before end: {item!r}")
        # Clip to the working day; ignore if entirely outside.
        s = max(b_start, start_of_day)
        e = min(b_end, end_of_day)
        if s < e:
            clipped.append((s, e))

    clipped.sort()

    # Merge overlapping / touching intervals.
    merged: list[list[int]] = []
    for s, e in clipped:
        if merged and s <= merged[-1][1]:
            if e > merged[-1][1]:
                merged[-1][1] = e
        else:
            merged.append([s, e])

    # Collect gaps.
    result: list[tuple[str, str]] = []
    cursor = start_of_day
    for s, e in merged:
        if s > cursor:
            length = s - cursor
            if length > 0 and length >= min_minutes:
                result.append((_format_time(cursor), _format_time(s)))
        if e > cursor:
            cursor = e
    if end_of_day > cursor:
        length = end_of_day - cursor
        if length > 0 and length >= min_minutes:
            result.append((_format_time(cursor), _format_time(end_of_day)))

    return result
