Write a Python 3.11+ module named `free_slots.py` that implements one function:

```python
def free_slots(busy, day_start, day_end, min_minutes=0) -> list[tuple[str, str]]:
```

It returns the free time windows in a working day, given a list of busy intervals.

Specification:

1. All times are strings in 24-hour "HH:MM" format with exactly two digits for hours and two for minutes. Valid values are "00:00" through "23:59", plus the special value "24:00" meaning end of day. Anything else (for example "9:00", "12:60", "25:00", "24:01", "ab:cd", "", non-string values) must raise `ValueError`.
2. `busy` is an iterable of 2-item tuples or lists `(start, end)`. Each interval is half-open: `[start, end)`. If `start >= end` for any busy interval, raise `ValueError`.
3. `day_start` must be strictly earlier than `day_end`, otherwise raise `ValueError`.
4. `min_minutes` is a non-negative integer. A negative value raises `ValueError`. Only free windows whose length in minutes is `>= min_minutes` are returned. Zero-length windows are never returned.
5. Busy intervals may be unsorted, may overlap, may touch each other (end of one equals start of the next), may extend partly outside the working day (clip them to the day), or may lie entirely outside the day (ignore them).
6. Return a list of `(start, end)` tuples of "HH:MM" strings (zero-padded, "24:00" allowed as an end), sorted by start, covering exactly the parts of `[day_start, day_end)` that are not busy and that satisfy rule 4.
7. Do not mutate the input.
8. Use only the standard library.

Example:

```python
free_slots([("10:00", "11:00"), ("09:30", "10:15"), ("13:00", "13:30")], "09:00", "17:00", 30)
# -> [("09:00", "09:30"), ("11:00", "13:00"), ("13:30", "17:00")]
```

Reply with the complete module in a single ```python fenced code block whose first line is `# file: free_slots.py`. Do not include tests.
