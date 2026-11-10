You are reviewing anonymous Python solutions to three coding tasks. All of them already pass the same hidden test suite, so focus on code quality: spec fidelity in edge cases the tests may not cover, robustness, readability, and maintainability. Be strict and specific. Do not guess which model or author wrote what.

==================== TASK a_free_slots ====================
SPEC:
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

---------- SOLUTION a_free_slots:S1 ----------
```python
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

```

---------- SOLUTION a_free_slots:S2 ----------
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

---------- SOLUTION a_free_slots:S3 ----------
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

---------- SOLUTION a_free_slots:S4 ----------
```python
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

```

==================== TASK b_invoice_bugfix ====================
SPEC:
You are fixing a bug in a small Python billing module. The module docstring describes the intended behaviour and is correct; the implementation is not.

Bug reports from the team:

1. "Totals are sometimes off by one cent compared with our spreadsheet."
2. "A customer ordered exactly 10 units and did not get the bulk discount."
3. "In the worker process, the second invoice we create sometimes already contains the first invoice's items."
4. "Customers with a coupon say the tax looks wrong."

There may be other places where the code disagrees with the docstring. Make the implementation match the docstring in every respect, keep the public API (class name, method names, argument names, return types) the same, and use only the standard library.

Here is the current file `invoice.py`:

```python
"""Small invoicing module used by the billing service.

Rules (these are the intended behaviour and are correct):

* Money is handled in Decimal. Every *returned* amount is rounded to cents
  using ROUND_HALF_UP (0.005 -> 0.01).
* A line is (sku, unit_price, quantity). quantity must be a positive int,
  unit_price must be >= 0, otherwise ValueError.
* Bulk discount: a line with quantity >= 10 gets 5% off that line.
* An optional invoice-level coupon is either a percentage string like
  "15%" (0-100 inclusive) or a fixed amount like "7.50". Anything else is
  ValueError. The coupon applies to the subtotal AFTER bulk discounts and
  BEFORE tax. A fixed coupon can never make the taxable amount negative
  (it is capped at the subtotal).
* Tax is applied to (subtotal - coupon) at the invoice tax rate (e.g. 0.08).
* summary() returns a dict with keys: subtotal, discount, tax, total, each a
  Decimal rounded to cents, where total == subtotal - discount + tax.
  "discount" is the coupon amount only (bulk discounts are already inside
  subtotal).
* Each Invoice is independent of every other Invoice.
"""
from decimal import Decimal, ROUND_HALF_UP


def _cents(x):
    return Decimal(round(float(x), 2))


class Invoice:
    def __init__(self, tax_rate="0.08", lines=[]):
        self.tax_rate = Decimal(tax_rate)
        self.lines = lines
        self.coupon = None

    def add_line(self, sku, unit_price, quantity):
        unit_price = Decimal(str(unit_price))
        if quantity <= 0 or unit_price < 0:
            raise ValueError("bad line")
        self.lines.append((sku, unit_price, quantity))

    def apply_coupon(self, coupon):
        self.coupon = coupon

    def _line_total(self, unit_price, quantity):
        total = unit_price * quantity
        if quantity > 10:
            total = total * Decimal("0.95")
        return total

    def _subtotal(self):
        return sum(self._line_total(p, q) for _, p, q in self.lines)

    def _coupon_amount(self, subtotal):
        if self.coupon is None:
            return Decimal(0)
        if self.coupon.endswith("%"):
            pct = Decimal(self.coupon[:-1])
            return subtotal * pct / 100
        return Decimal(self.coupon)

    def summary(self):
        subtotal = self._subtotal()
        tax = subtotal * self.tax_rate
        discount = self._coupon_amount(subtotal + tax)
        total = subtotal + tax - discount
        return {
            "subtotal": _cents(subtotal),
            "discount": _cents(discount),
            "tax": _cents(tax),
            "total": _cents(total),
        }
```

Reply with the complete fixed module in a single ```python fenced code block whose first line is `# file: invoice.py`. After the code block, list each bug you fixed in one line each. Do not include tests.

---------- SOLUTION b_invoice_bugfix:S1 ----------
```python
# file: invoice.py
"""Small invoicing module used by the billing service.

Rules (these are the intended behaviour and are correct):

* Money is handled in Decimal. Every *returned* amount is rounded to cents
  using ROUND_HALF_UP (0.005 -> 0.01).
* A line is (sku, unit_price, quantity). quantity must be a positive int,
  unit_price must be >= 0, otherwise ValueError.
* Bulk discount: a line with quantity >= 10 gets 5% off that line.
* An optional invoice-level coupon is either a percentage string like
  "15%" (0-100 inclusive) or a fixed amount like "7.50". Anything else is
  ValueError. The coupon applies to the subtotal AFTER bulk discounts and
  BEFORE tax. A fixed coupon can never make the taxable amount negative
  (it is capped at the subtotal).
* Tax is applied to (subtotal - coupon) at the invoice tax rate (e.g. 0.08).
* summary() returns a dict with keys: subtotal, discount, tax, total, each a
  Decimal rounded to cents, where total == subtotal - discount + tax.
  "discount" is the coupon amount only (bulk discounts are already inside
  subtotal).
* Each Invoice is independent of every other Invoice.
"""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

_CENT = Decimal("0.01")
_BULK_THRESHOLD = 10
_BULK_FACTOR = Decimal("0.95")


def _cents(x):
    return Decimal(x).quantize(_CENT, rounding=ROUND_HALF_UP)


def _to_decimal(value, what):
    """Convert value to a finite Decimal or raise ValueError."""
    if isinstance(value, bool):
        raise ValueError("bad %s: %r" % (what, value))
    try:
        result = value if isinstance(value, Decimal) else Decimal(str(value).strip())
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError("bad %s: %r" % (what, value)) from None
    if not result.is_finite():
        raise ValueError("bad %s: %r" % (what, value))
    return result


def _parse_coupon(coupon):
    """Return ("percent", Decimal) or ("fixed", Decimal); ValueError if invalid."""
    if not isinstance(coupon, str):
        raise ValueError("bad coupon: %r" % (coupon,))
    text = coupon.strip()
    if text.endswith("%"):
        pct = _to_decimal(text[:-1], "coupon")
        if pct < 0 or pct > 100:
            raise ValueError("bad coupon: %r" % (coupon,))
        return "percent", pct
    amount = _to_decimal(text, "coupon")
    if amount < 0:
        raise ValueError("bad coupon: %r" % (coupon,))
    return "fixed", amount


class Invoice:
    def __init__(self, tax_rate="0.08", lines=None):
        self.tax_rate = _to_decimal(tax_rate, "tax rate")
        self.lines = []
        self.coupon = None
        if lines is not None:
            for line in lines:
                try:
                    sku, unit_price, quantity = line
                except (TypeError, ValueError):
                    raise ValueError("bad line") from None
                self.add_line(sku, unit_price, quantity)

    def add_line(self, sku, unit_price, quantity):
        if isinstance(quantity, bool) or not isinstance(quantity, int):
            raise ValueError("bad line")
        unit_price = _to_decimal(unit_price, "unit price")
        if quantity <= 0 or unit_price < 0:
            raise ValueError("bad line")
        self.lines.append((sku, unit_price, quantity))

    def apply_coupon(self, coupon):
        if coupon is not None:
            _parse_coupon(coupon)  # validate now; raises ValueError if invalid
        self.coupon = coupon

    def _line_total(self, unit_price, quantity):
        total = unit_price * quantity
        if quantity >= _BULK_THRESHOLD:
            total = total * _BULK_FACTOR
        return total

    def _subtotal(self):
        return sum(
            (self._line_total(p, q) for _, p, q in self.lines), Decimal(0)
        )

    def _coupon_amount(self, subtotal):
        if self.coupon is None:
            return Decimal(0)
        kind, value = _parse_coupon(self.coupon)
        if kind == "percent":
            return subtotal * value / 100
        return min(value, subtotal)

    def summary(self):
        subtotal = self._subtotal()
        discount = self._coupon_amount(subtotal)
        tax = (subtotal - discount) * self.tax_rate

        subtotal_c = _cents(subtotal)
        discount_c = _cents(discount)
        tax_c = _cents(tax)
        return {
            "subtotal": subtotal_c,
            "discount": discount_c,
            "tax": tax_c,
            "total": subtotal_c - discount_c + tax_c,
        }

```

---------- SOLUTION b_invoice_bugfix:S2 ----------
```python
# file: invoice.py
"""Small invoicing module used by the billing service.

Rules (these are the intended behaviour and are correct):

* Money is handled in Decimal. Every *returned* amount is rounded to cents
  using ROUND_HALF_UP (0.005 -> 0.01).
* A line is (sku, unit_price, quantity). quantity must be a positive int,
  unit_price must be >= 0, otherwise ValueError.
* Bulk discount: a line with quantity >= 10 gets 5% off that line.
* An optional invoice-level coupon is either a percentage string like
  "15%" (0-100 inclusive) or a fixed amount like "7.50". Anything else is
  ValueError. The coupon applies to the subtotal AFTER bulk discounts and
  BEFORE tax. A fixed coupon can never make the taxable amount negative
  (it is capped at the subtotal).
* Tax is applied to (subtotal - coupon) at the invoice tax rate (e.g. 0.08).
* summary() returns a dict with keys: subtotal, discount, tax, total, each a
  Decimal rounded to cents, where total == subtotal - discount + tax.
  "discount" is the coupon amount only (bulk discounts are already inside
  subtotal).
* Each Invoice is independent of every other Invoice.
"""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

_CENT = Decimal("0.01")
_BULK_QUANTITY = 10
_BULK_FACTOR = Decimal("0.95")


def _cents(x):
    return Decimal(x).quantize(_CENT, rounding=ROUND_HALF_UP)


def _to_decimal(value, what):
    """Convert value to a finite Decimal or raise ValueError."""
    if isinstance(value, bool):
        raise ValueError("bad %s: %r" % (what, value))
    try:
        if isinstance(value, Decimal):
            result = value
        else:
            result = Decimal(str(value).strip())
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError("bad %s: %r" % (what, value)) from None
    if not result.is_finite():
        raise ValueError("bad %s: %r" % (what, value))
    return result


def _parse_coupon(coupon):
    """Return ("percent" | "fixed", Decimal) or raise ValueError."""
    if not isinstance(coupon, str):
        raise ValueError("bad coupon: %r" % (coupon,))
    text = coupon.strip()
    if text.endswith("%"):
        pct = _to_decimal(text[:-1], "coupon")
        if pct < 0 or pct > 100:
            raise ValueError("bad coupon: %r" % (coupon,))
        return "percent", pct
    amount = _to_decimal(text, "coupon")
    if amount < 0:
        raise ValueError("bad coupon: %r" % (coupon,))
    return "fixed", amount


class Invoice:
    def __init__(self, tax_rate="0.08", lines=None):
        self.tax_rate = _to_decimal(tax_rate, "tax rate")
        self.lines = []
        self.coupon = None
        if lines is not None:
            for sku, unit_price, quantity in lines:
                self.add_line(sku, unit_price, quantity)

    def add_line(self, sku, unit_price, quantity):
        if isinstance(quantity, bool) or not isinstance(quantity, int):
            raise ValueError("bad line: quantity must be a positive int")
        if quantity <= 0:
            raise ValueError("bad line: quantity must be a positive int")
        unit_price = _to_decimal(unit_price, "unit price")
        if unit_price < 0:
            raise ValueError("bad line: unit_price must be >= 0")
        self.lines.append((sku, unit_price, quantity))

    def apply_coupon(self, coupon):
        if coupon is not None:
            _parse_coupon(coupon)  # validate now; raises ValueError
        self.coupon = coupon

    def _line_total(self, unit_price, quantity):
        total = unit_price * quantity
        if quantity >= _BULK_QUANTITY:
            total = total * _BULK_FACTOR
        return total

    def _subtotal(self):
        return sum(
            (self._line_total(p, q) for _, p, q in self.lines),
            Decimal(0),
        )

    def _coupon_amount(self, subtotal):
        if self.coupon is None:
            return Decimal(0)
        kind, value = _parse_coupon(self.coupon)
        if kind == "percent":
            return subtotal * value / 100
        return min(value, subtotal)

    def summary(self):
        subtotal = self._subtotal()
        discount = self._coupon_amount(subtotal)
        tax = (subtotal - discount) * self.tax_rate

        subtotal_c = _cents(subtotal)
        discount_c = _cents(discount)
        tax_c = _cents(tax)
        return {
            "subtotal": subtotal_c,
            "discount": discount_c,
            "tax": tax_c,
            "total": subtotal_c - discount_c + tax_c,
        }

```

---------- SOLUTION b_invoice_bugfix:S3 ----------
```python
# file: invoice.py
"""Small invoicing module used by the billing service.

Rules (these are the intended behaviour and are correct):

* Money is handled in Decimal. Every *returned* amount is rounded to cents
  using ROUND_HALF_UP (0.005 -> 0.01).
* A line is (sku, unit_price, quantity). quantity must be a positive int,
  unit_price must be >= 0, otherwise ValueError.
* Bulk discount: a line with quantity >= 10 gets 5% off that line.
* An optional invoice-level coupon is either a percentage string like
  "15%" (0-100 inclusive) or a fixed amount like "7.50". Anything else is
  ValueError. The coupon applies to the subtotal AFTER bulk discounts and
  BEFORE tax. A fixed coupon can never make the taxable amount negative
  (it is capped at the subtotal).
* Tax is applied to (subtotal - coupon) at the invoice tax rate (e.g. 0.08).
* summary() returns a dict with keys: subtotal, discount, tax, total, each a
  Decimal rounded to cents, where total == subtotal - discount + tax.
  "discount" is the coupon amount only (bulk discounts are already inside
  subtotal).
* Each Invoice is independent of every other Invoice.
"""
import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

_CENT = Decimal("0.01")
_NUMBER_RE = re.compile(r"^(?:\d+(?:\.\d*)?|\.\d+)$")


def _cents(x):
    """Round a Decimal to cents using ROUND_HALF_UP (no float conversion)."""
    return Decimal(x).quantize(_CENT, rounding=ROUND_HALF_UP)


def _to_decimal(value, what):
    """Convert value to a finite Decimal, raising ValueError on failure."""
    if isinstance(value, bool):
        raise ValueError("bad %s: %r" % (what, value))
    try:
        d = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError("bad %s: %r" % (what, value))
    if not d.is_finite():
        raise ValueError("bad %s: %r" % (what, value))
    return d


class Invoice:
    def __init__(self, tax_rate="0.08", lines=None):
        self.tax_rate = _to_decimal(tax_rate, "tax rate")
        # Each invoice owns its own list; never share a mutable default.
        self.lines = []
        self.coupon = None
        if lines is not None:
            for line in lines:
                sku, unit_price, quantity = line
                self.add_line(sku, unit_price, quantity)

    def add_line(self, sku, unit_price, quantity):
        if isinstance(quantity, bool) or not isinstance(quantity, int):
            raise ValueError("quantity must be a positive int")
        if quantity <= 0:
            raise ValueError("quantity must be a positive int")
        unit_price = _to_decimal(unit_price, "unit price")
        if unit_price < 0:
            raise ValueError("unit_price must be >= 0")
        self.lines.append((sku, unit_price, quantity))

    def apply_coupon(self, coupon):
        if coupon is None:
            self.coupon = None
            return
        if not isinstance(coupon, str):
            raise ValueError("bad coupon: %r" % (coupon,))
        text = coupon.strip()
        if text.endswith("%"):
            number = text[:-1]
            if not _NUMBER_RE.match(number):
                raise ValueError("bad coupon: %r" % (coupon,))
            pct = Decimal(number)
            if pct < 0 or pct > 100:
                raise ValueError("coupon percentage must be 0-100")
        else:
            if not _NUMBER_RE.match(text):
                raise ValueError("bad coupon: %r" % (coupon,))
        self.coupon = text

    def _line_total(self, unit_price, quantity):
        total = unit_price * quantity
        if quantity >= 10:
            total = total * Decimal("0.95")
        return total

    def _subtotal(self):
        return sum(
            (self._line_total(p, q) for _, p, q in self.lines), Decimal(0)
        )

    def _coupon_amount(self, subtotal):
        if self.coupon is None:
            return Decimal(0)
        if self.coupon.endswith("%"):
            pct = Decimal(self.coupon[:-1])
            return subtotal * pct / 100
        return min(Decimal(self.coupon), subtotal)

    def summary(self):
        subtotal = _cents(self._subtotal())
        discount = _cents(self._coupon_amount(subtotal))
        if discount > subtotal:
            discount = subtotal
        taxable = subtotal - discount
        tax = _cents(taxable * self.tax_rate)
        total = subtotal - discount + tax
        return {
            "subtotal": subtotal,
            "discount": discount,
            "tax": tax,
            "total": total,
        }

```

---------- SOLUTION b_invoice_bugfix:S4 ----------
```python
# file: invoice.py
"""Small invoicing module used by the billing service.

Rules (these are the intended behaviour and are correct):

* Money is handled in Decimal. Every *returned* amount is rounded to cents
  using ROUND_HALF_UP (0.005 -> 0.01).
* A line is (sku, unit_price, quantity). quantity must be a positive int,
  unit_price must be >= 0, otherwise ValueError.
* Bulk discount: a line with quantity >= 10 gets 5% off that line.
* An optional invoice-level coupon is either a percentage string like
  "15%" (0-100 inclusive) or a fixed amount like "7.50". Anything else is
  ValueError. The coupon applies to the subtotal AFTER bulk discounts and
  BEFORE tax. A fixed coupon can never make the taxable amount negative
  (it is capped at the subtotal).
* Tax is applied to (subtotal - coupon) at the invoice tax rate (e.g. 0.08).
* summary() returns a dict with keys: subtotal, discount, tax, total, each a
  Decimal rounded to cents, where total == subtotal - discount + tax.
  "discount" is the coupon amount only (bulk discounts are already inside
  subtotal).
* Each Invoice is independent of every other Invoice.
"""
import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

_CENT = Decimal("0.01")
_BULK_QTY = 10
_BULK_FACTOR = Decimal("0.95")
_NUMBER = r"(?:\d+(?:\.\d*)?|\.\d+)"
_PCT_RE = re.compile(r"^(" + _NUMBER + r")%$")
_FIXED_RE = re.compile(r"^(" + _NUMBER + r")$")


def _cents(x):
    return Decimal(x).quantize(_CENT, rounding=ROUND_HALF_UP)


def _to_decimal(value):
    try:
        d = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError("invalid number: %r" % (value,))
    if not d.is_finite():
        raise ValueError("invalid number: %r" % (value,))
    return d


class Invoice:
    def __init__(self, tax_rate="0.08", lines=None):
        self.tax_rate = _to_decimal(tax_rate)
        self.lines = []
        self.coupon = None
        if lines is not None:
            for line in lines:
                self.add_line(*line)

    def add_line(self, sku, unit_price, quantity):
        if isinstance(quantity, bool) or not isinstance(quantity, int):
            raise ValueError("bad line: quantity must be a positive int")
        if quantity <= 0:
            raise ValueError("bad line: quantity must be a positive int")
        unit_price = _to_decimal(unit_price)
        if unit_price < 0:
            raise ValueError("bad line: unit_price must be >= 0")
        self.lines.append((sku, unit_price, quantity))

    def apply_coupon(self, coupon):
        if coupon is None:
            self.coupon = None
            return
        if not isinstance(coupon, str):
            raise ValueError("bad coupon: %r" % (coupon,))
        m = _PCT_RE.match(coupon)
        if m:
            pct = Decimal(m.group(1))
            if not (Decimal(0) <= pct <= Decimal(100)):
                raise ValueError("bad coupon: percentage must be 0-100")
            self.coupon = ("pct", pct)
            return
        m = _FIXED_RE.match(coupon)
        if m:
            self.coupon = ("fixed", Decimal(m.group(1)))
            return
        raise ValueError("bad coupon: %r" % (coupon,))

    def _line_total(self, unit_price, quantity):
        total = unit_price * quantity
        if quantity >= _BULK_QTY:
            total = total * _BULK_FACTOR
        return total

    def _subtotal(self):
        return sum(
            (self._line_total(p, q) for _, p, q in self.lines), Decimal(0)
        )

    def _coupon_amount(self, subtotal):
        if self.coupon is None:
            return Decimal(0)
        kind, value = self.coupon
        if kind == "pct":
            return subtotal * value / Decimal(100)
        return min(value, subtotal)

    def summary(self):
        subtotal = self._subtotal()
        discount = self._coupon_amount(subtotal)
        tax = (subtotal - discount) * self.tax_rate
        subtotal_c = _cents(subtotal)
        discount_c = _cents(discount)
        tax_c = _cents(tax)
        total_c = subtotal_c - discount_c + tax_c
        return {
            "subtotal": subtotal_c,
            "discount": discount_c,
            "tax": tax_c,
            "total": total_c,
        }

```

==================== TASK c_ttl_cache ====================
SPEC:
Build a small two-file Python 3.11+ feature using only the standard library: a thread-safe LRU cache with per-entry time-to-live, plus a command-line front end.

File 1: `ttlcache.py`

```python
class TTLCache:
    def __init__(self, maxsize: int, ttl: float, clock=time.monotonic): ...
    def set(self, key, value, ttl: float | None = None) -> None: ...
    def get(self, key, default=None): ...
    def delete(self, key) -> bool: ...
    def __contains__(self, key) -> bool: ...
    def __len__(self) -> int: ...
    def stats(self) -> dict: ...
```

Rules:

1. `maxsize` must be an int >= 1 and `ttl` must be a number > 0, otherwise raise `ValueError`. A per-call `ttl` passed to `set` overrides the default for that entry and must also be > 0 (else `ValueError`).
2. `clock` is a zero-argument callable returning the current time in seconds. All expiry decisions must use it (tests inject a fake clock).
3. An entry set at time `t` with ttl `x` is live while `clock() < t + x` and expired when `clock() >= t + x`.
4. `get` returns the value for a live key and marks it most recently used (hit). For a missing or expired key it returns `default` (miss). An expired entry found by any operation is removed at that moment.
5. `set` on an existing key replaces the value, resets its expiry from now, and marks it most recently used. It is not an eviction.
6. When `set` inserts a new key and the cache already holds `maxsize` entries, first remove all expired entries; if it is still full, evict the least recently used entry.
7. `delete` removes a key and returns True if a live entry was removed, else False.
8. `key in cache` is True only for live entries. It does not count as a hit or miss and does not change recency.
9. `len(cache)` returns the number of live entries.
10. `stats()` returns a new dict with exactly these int keys: `hits`, `misses`, `evictions` (LRU evictions only), `expirations` (number of expired entries removed, for any reason).
11. All public methods must be safe to call from multiple threads at once.

File 2: `cache_cli.py`

A CLI run as `python cache_cli.py [--maxsize N] [--ttl SECONDS]` (defaults: maxsize 128, ttl 60). It creates one `TTLCache` (real clock) and reads commands from standard input, one per line, until EOF. Tokens are separated by whitespace. Commands are case-insensitive; keys and values are case-sensitive. For each non-blank line it prints exactly one line to standard output:

- `SET key value` or `SET key value ttl` -> `OK`
- `GET key` -> the value, or `(nil)` if missing/expired
- `DEL key` -> `1` if removed, else `0`
- `LEN` -> the number of live entries
- `STATS` -> the stats dict as JSON with sorted keys, for example `{"evictions": 0, "expirations": 0, "hits": 1, "misses": 0}`
- Unknown command, wrong number of arguments, or an invalid ttl -> `ERR <short message>`; processing continues with the next line.

Blank lines are ignored. The process exits with status 0 at EOF. Invalid `--maxsize`/`--ttl` values should make the program exit with a non-zero status.

Reply with exactly two ```python fenced code blocks. The first line of the first block must be `# file: ttlcache.py` and the first line of the second must be `# file: cache_cli.py`. Do not include tests.

---------- SOLUTION c_ttl_cache:S1 ----------
```python
# file: cache_cli.py
"""Command-line front end for TTLCache.

Usage: python cache_cli.py [--maxsize N] [--ttl SECONDS]
Reads commands from standard input, one per line, until EOF.
"""

from __future__ import annotations

import argparse
import json
import sys

from ttlcache import TTLCache


def _parse_args(argv: list[str] | None) -> tuple[argparse.ArgumentParser, argparse.Namespace]:
    parser = argparse.ArgumentParser(description="Interactive TTL LRU cache.")
    parser.add_argument("--maxsize", type=int, default=128,
                        help="maximum number of entries (int >= 1, default 128)")
    parser.add_argument("--ttl", type=float, default=60.0,
                        help="default time-to-live in seconds (> 0, default 60)")
    return parser, parser.parse_args(argv)


def handle_line(cache: TTLCache, line: str) -> str | None:
    """Process one input line. Return the output line, or None for blank lines."""
    tokens = line.split()
    if not tokens:
        return None
    cmd, args = tokens[0].upper(), tokens[1:]

    if cmd == "SET":
        if len(args) not in (2, 3):
            return "ERR wrong number of arguments for SET"
        key, value = args[0], args[1]
        ttl = None
        if len(args) == 3:
            try:
                ttl = float(args[2])
            except ValueError:
                return "ERR invalid ttl"
        try:
            cache.set(key, value, ttl)
        except ValueError:
            return "ERR invalid ttl"
        return "OK"

    if cmd == "GET":
        if len(args) != 1:
            return "ERR wrong number of arguments for GET"
        value = cache.get(args[0])
        return "(nil)" if value is None else str(value)

    if cmd == "DEL":
        if len(args) != 1:
            return "ERR wrong number of arguments for DEL"
        return "1" if cache.delete(args[0]) else "0"

    if cmd == "LEN":
        if args:
            return "ERR wrong number of arguments for LEN"
        return str(len(cache))

    if cmd == "STATS":
        if args:
            return "ERR wrong number of arguments for STATS"
        return json.dumps(cache.stats(), sort_keys=True)

    return "ERR unknown command"


def main(argv: list[str] | None = None) -> int:
    parser, args = _parse_args(argv)
    try:
        cache = TTLCache(args.maxsize, args.ttl)
    except ValueError as exc:
        parser.error(str(exc))  # exits with status 2

    for line in sys.stdin:
        out = handle_line(cache, line)
        if out is not None:
            print(out, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())

# file: ttlcache.py
"""Thread-safe LRU cache with per-entry time-to-live (standard library only)."""

from __future__ import annotations

import numbers
import threading
import time
from collections import OrderedDict
from typing import Any, Callable

__all__ = ["TTLCache"]


def _is_number(value: Any) -> bool:
    return isinstance(value, numbers.Real) and not isinstance(value, bool)


def _validate_ttl(ttl: Any, name: str = "ttl") -> float:
    # "not ttl > 0" also rejects NaN.
    if not _is_number(ttl) or not ttl > 0:
        raise ValueError(f"{name} must be a number > 0, got {ttl!r}")
    return ttl


class TTLCache:
    """An LRU cache whose entries expire after a time-to-live.

    An entry set at time ``t`` with ttl ``x`` is live while ``clock() < t + x``
    and expired once ``clock() >= t + x``.
    """

    def __init__(self, maxsize: int, ttl: float, clock: Callable[[], float] = time.monotonic):
        if not isinstance(maxsize, int) or isinstance(maxsize, bool) or maxsize < 1:
            raise ValueError(f"maxsize must be an int >= 1, got {maxsize!r}")
        _validate_ttl(ttl)
        if not callable(clock):
            raise ValueError("clock must be a zero-argument callable")

        self._maxsize = maxsize
        self._ttl = ttl
        self._clock = clock
        # key -> (value, expires_at); order is LRU (first) to MRU (last).
        self._data: OrderedDict[Any, tuple[Any, float]] = OrderedDict()
        self._lock = threading.RLock()
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._expirations = 0

    # ----- internal helpers (caller must hold the lock) -----

    def _expire_if_needed(self, key: Any, now: float) -> bool:
        """Remove ``key`` if present and expired. Return True if it was removed."""
        entry = self._data.get(key)
        if entry is not None and now >= entry[1]:
            del self._data[key]
            self._expirations += 1
            return True
        return False

    def _purge_expired(self, now: float) -> None:
        expired = [k for k, (_, exp) in self._data.items() if now >= exp]
        for k in expired:
            del self._data[k]
        self._expirations += len(expired)

    # ----- public API -----

    def set(self, key: Any, value: Any, ttl: float | None = None) -> None:
        if ttl is None:
            ttl = self._ttl
        else:
            _validate_ttl(ttl)
        with self._lock:
            now = self._clock()
            expires_at = now + ttl
            self._expire_if_needed(key, now)
            if key in self._data:
                # Replacement: new value, new expiry, most recently used.
                self._data[key] = (value, expires_at)
                self._data.move_to_end(key)
                return
            if len(self._data) >= self._maxsize:
                self._purge_expired(now)
                if len(self._data) >= self._maxsize:
                    self._data.popitem(last=False)
                    self._evictions += 1
            self._data[key] = (value, expires_at)

    def get(self, key: Any, default: Any = None) -> Any:
        with self._lock:
            now = self._clock()
            if self._expire_if_needed(key, now) or key not in self._data:
                self._misses += 1
                return default
            self._data.move_to_end(key)
            self._hits += 1
            return self._data[key][0]

    def delete(self, key: Any) -> bool:
        with self._lock:
            now = self._clock()
            if self._expire_if_needed(key, now):
                return False
            if key in self._data:
                del self._data[key]
                return True
            return False

    def __contains__(self, key: Any) -> bool:
        with self._lock:
            now = self._clock()
            if self._expire_if_needed(key, now):
                return False
            return key in self._data

    def __len__(self) -> int:
        with self._lock:
            self._purge_expired(self._clock())
            return len(self._data)

    def stats(self) -> dict:
        with self._lock:
            return {
                "hits": self._hits,
                "misses": self._misses,
                "evictions": self._evictions,
                "expirations": self._expirations,
            }

    def __repr__(self) -> str:
        return f"{type(self).__name__}(maxsize={self._maxsize!r}, ttl={self._ttl!r})"

```

---------- SOLUTION c_ttl_cache:S2 ----------
```python
# file: cache_cli.py
"""Command-line front end for TTLCache: reads commands from standard input."""

import argparse
import json
import os
import sys

from ttlcache import TTLCache


def execute(cache: TTLCache, tokens: list[str]) -> str:
    cmd = tokens[0].upper()
    args = tokens[1:]

    if cmd == "SET":
        if len(args) not in (2, 3):
            return "ERR wrong number of arguments for SET"
        ttl = None
        if len(args) == 3:
            try:
                ttl = float(args[2])
            except ValueError:
                return "ERR invalid ttl"
        try:
            cache.set(args[0], args[1], ttl)
        except ValueError:
            return "ERR invalid ttl"
        return "OK"

    if cmd == "GET":
        if len(args) != 1:
            return "ERR wrong number of arguments for GET"
        value = cache.get(args[0])
        return "(nil)" if value is None else value

    if cmd == "DEL":
        if len(args) != 1:
            return "ERR wrong number of arguments for DEL"
        return "1" if cache.delete(args[0]) else "0"

    if cmd == "LEN":
        if args:
            return "ERR wrong number of arguments for LEN"
        return str(len(cache))

    if cmd == "STATS":
        if args:
            return "ERR wrong number of arguments for STATS"
        return json.dumps(cache.stats(), sort_keys=True)

    return "ERR unknown command"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="TTL/LRU cache command shell")
    parser.add_argument("--maxsize", type=int, default=128)
    parser.add_argument("--ttl", type=float, default=60.0)
    ns = parser.parse_args(argv)  # exits with status 2 on unparseable values

    try:
        cache = TTLCache(ns.maxsize, ns.ttl)
    except ValueError as exc:
        parser.error(str(exc))  # exits with status 2

    try:
        for line in sys.stdin:
            tokens = line.split()
            if not tokens:
                continue
            print(execute(cache, tokens), flush=True)
    except BrokenPipeError:
        # Reader went away; avoid a second error when stdout is flushed at exit.
        try:
            os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        except (OSError, ValueError):
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())

# file: ttlcache.py
"""Thread-safe LRU cache with per-entry time-to-live (standard library only)."""

import threading
import time
from collections import OrderedDict
from numbers import Real

__all__ = ["TTLCache"]


def _valid_ttl(ttl) -> bool:
    # Must be a real number > 0. bool is rejected; NaN fails the comparison.
    return isinstance(ttl, Real) and not isinstance(ttl, bool) and ttl > 0


class TTLCache:
    def __init__(self, maxsize: int, ttl: float, clock=time.monotonic):
        if not isinstance(maxsize, int) or isinstance(maxsize, bool) or maxsize < 1:
            raise ValueError("maxsize must be an int >= 1")
        if not _valid_ttl(ttl):
            raise ValueError("ttl must be a number > 0")
        if not callable(clock):
            raise TypeError("clock must be callable")
        self._maxsize = maxsize
        self._ttl = ttl
        self._clock = clock
        self._lock = threading.RLock()
        # key -> (value, expires_at); order: least recently used first.
        self._data: OrderedDict = OrderedDict()
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._expirations = 0

    # ---- internal helpers (must be called with the lock held) ----

    def _purge_expired(self, now) -> None:
        expired = [k for k, (_, exp) in self._data.items() if now >= exp]
        for k in expired:
            del self._data[k]
        self._expirations += len(expired)

    def _live_entry(self, key, now):
        """Return the (value, expires_at) entry if live; drop it if expired."""
        entry = self._data.get(key)
        if entry is None:
            return None
        if now >= entry[1]:
            del self._data[key]
            self._expirations += 1
            return None
        return entry

    # ---- public API ----

    def set(self, key, value, ttl: float | None = None) -> None:
        if ttl is None:
            ttl = self._ttl
        elif not _valid_ttl(ttl):
            raise ValueError("ttl must be a number > 0")
        with self._lock:
            now = self._clock()
            if self._live_entry(key, now) is not None:
                # Replace: new value, new expiry, most recently used.
                self._data[key] = (value, now + ttl)
                self._data.move_to_end(key)
                return
            # New key (or the previous entry had expired and was removed).
            if len(self._data) >= self._maxsize:
                self._purge_expired(now)
                if len(self._data) >= self._maxsize:
                    self._data.popitem(last=False)
                    self._evictions += 1
            self._data[key] = (value, now + ttl)

    def get(self, key, default=None):
        with self._lock:
            entry = self._live_entry(key, self._clock())
            if entry is None:
                self._misses += 1
                return default
            self._data.move_to_end(key)
            self._hits += 1
            return entry[0]

    def delete(self, key) -> bool:
        with self._lock:
            if self._live_entry(key, self._clock()) is None:
                return False
            del self._data[key]
            return True

    def __contains__(self, key) -> bool:
        with self._lock:
            return self._live_entry(key, self._clock()) is not None

    def __len__(self) -> int:
        with self._lock:
            self._purge_expired(self._clock())
            return len(self._data)

    def stats(self) -> dict:
        with self._lock:
            return {
                "hits": self._hits,
                "misses": self._misses,
                "evictions": self._evictions,
                "expirations": self._expirations,
            }

```

---------- SOLUTION c_ttl_cache:S3 ----------
```python
# file: cache_cli.py
"""Command-line front end for TTLCache. Reads commands from standard input."""

import argparse
import json
import os
import sys

from ttlcache import TTLCache


def handle(cache: TTLCache, tokens: list[str]) -> str:
    cmd = tokens[0].upper()
    args = tokens[1:]

    if cmd == "SET":
        if len(args) not in (2, 3):
            return "ERR wrong number of arguments for SET"
        ttl = None
        if len(args) == 3:
            try:
                ttl = float(args[2])
            except ValueError:
                return "ERR invalid ttl"
        try:
            cache.set(args[0], args[1], ttl)
        except ValueError:
            return "ERR invalid ttl"
        return "OK"

    if cmd == "GET":
        if len(args) != 1:
            return "ERR wrong number of arguments for GET"
        value = cache.get(args[0])
        return "(nil)" if value is None else value

    if cmd == "DEL":
        if len(args) != 1:
            return "ERR wrong number of arguments for DEL"
        return "1" if cache.delete(args[0]) else "0"

    if cmd == "LEN":
        if args:
            return "ERR wrong number of arguments for LEN"
        return str(len(cache))

    if cmd == "STATS":
        if args:
            return "ERR wrong number of arguments for STATS"
        return json.dumps(cache.stats(), sort_keys=True)

    return "ERR unknown command"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="TTL/LRU cache command shell")
    parser.add_argument("--maxsize", type=int, default=128)
    parser.add_argument("--ttl", type=float, default=60.0)
    ns = parser.parse_args(argv)  # exits with status 2 on unparseable values

    try:
        cache = TTLCache(ns.maxsize, ns.ttl)
    except ValueError as exc:
        parser.error(str(exc))  # exits with status 2

    try:
        for line in sys.stdin:
            tokens = line.split()
            if not tokens:
                continue
            print(handle(cache, tokens), flush=True)
    except BrokenPipeError:
        # Reader went away; avoid a second error when stdout is flushed at exit.
        try:
            os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        except (OSError, ValueError):
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())

# file: ttlcache.py
"""Thread-safe LRU cache with per-entry time-to-live (standard library only)."""

import math
import numbers
import threading
import time
from collections import OrderedDict

__all__ = ["TTLCache"]


def _check_ttl(ttl):
    # Rejects non-numbers, bools, NaN, zero and negatives.
    if (
        isinstance(ttl, bool)
        or not isinstance(ttl, numbers.Real)
        or not ttl > 0
    ):
        raise ValueError("ttl must be a number > 0")
    return ttl


class TTLCache:
    def __init__(self, maxsize: int, ttl: float, clock=time.monotonic):
        if isinstance(maxsize, bool) or not isinstance(maxsize, int) or maxsize < 1:
            raise ValueError("maxsize must be an int >= 1")
        self._maxsize = maxsize
        self._ttl = _check_ttl(ttl)
        self._clock = clock
        self._lock = threading.RLock()
        # key -> (value, expires_at); order: least recently used first.
        self._data = OrderedDict()
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._expirations = 0

    # -- internal helpers (call with the lock held) ---------------------

    def _purge_expired(self, now) -> None:
        dead = [k for k, (_, exp) in self._data.items() if now >= exp]
        for k in dead:
            del self._data[k]
        self._expirations += len(dead)

    # -- public API -------------------------------------------------------

    def set(self, key, value, ttl: float | None = None) -> None:
        ttl = self._ttl if ttl is None else _check_ttl(ttl)
        with self._lock:
            now = self._clock()
            try:
                expires = now + ttl
            except OverflowError:
                expires = math.inf

            entry = self._data.get(key)
            if entry is not None:
                if now >= entry[1]:
                    # Expired entry found: remove it, then treat as new insert.
                    del self._data[key]
                    self._expirations += 1
                else:
                    self._data[key] = (value, expires)
                    self._data.move_to_end(key)
                    return

            if len(self._data) >= self._maxsize:
                self._purge_expired(now)
                if len(self._data) >= self._maxsize:
                    self._data.popitem(last=False)
                    self._evictions += 1
            self._data[key] = (value, expires)

    def get(self, key, default=None):
        with self._lock:
            entry = self._data.get(key)
            if entry is None:
                self._misses += 1
                return default
            if self._clock() >= entry[1]:
                del self._data[key]
                self._expirations += 1
                self._misses += 1
                return default
            self._data.move_to_end(key)
            self._hits += 1
            return entry[0]

    def delete(self, key) -> bool:
        with self._lock:
            entry = self._data.get(key)
            if entry is None:
                return False
            del self._data[key]
            if self._clock() >= entry[1]:
                self._expirations += 1
                return False
            return True

    def __contains__(self, key) -> bool:
        with self._lock:
            entry = self._data.get(key)
            if entry is None:
                return False
            if self._clock() >= entry[1]:
                del self._data[key]
                self._expirations += 1
                return False
            return True

    def __len__(self) -> int:
        with self._lock:
            self._purge_expired(self._clock())
            return len(self._data)

    def stats(self) -> dict:
        with self._lock:
            return {
                "hits": self._hits,
                "misses": self._misses,
                "evictions": self._evictions,
                "expirations": self._expirations,
            }

```

---------- SOLUTION c_ttl_cache:S4 ----------
```python
# file: cache_cli.py
"""Command-line front end for TTLCache.

Usage: python cache_cli.py [--maxsize N] [--ttl SECONDS]

Reads commands from stdin, one per line, and prints one line per command.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from typing import TextIO

from ttlcache import TTLCache


def _positive_int(text: str) -> int:
    try:
        value = int(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"invalid int value: {text!r}")
    if value < 1:
        raise argparse.ArgumentTypeError("must be >= 1")
    return value


def _positive_float(text: str) -> float:
    try:
        value = float(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"invalid number: {text!r}")
    if math.isnan(value) or value <= 0:
        raise argparse.ArgumentTypeError("must be a number > 0")
    return value


def _parse_ttl(text: str) -> float | None:
    try:
        value = float(text)
    except ValueError:
        return None
    if math.isnan(value) or value <= 0:
        return None
    return value


def handle_line(cache: TTLCache, line: str) -> str | None:
    """Process one input line; return the output line, or None if blank."""
    tokens = line.split()
    if not tokens:
        return None
    cmd = tokens[0].upper()
    args = tokens[1:]

    if cmd == "SET":
        if len(args) not in (2, 3):
            return "ERR wrong number of arguments for SET"
        key, value = args[0], args[1]
        if len(args) == 3:
            ttl = _parse_ttl(args[2])
            if ttl is None:
                return "ERR invalid ttl"
            try:
                cache.set(key, value, ttl)
            except ValueError:
                return "ERR invalid ttl"
        else:
            cache.set(key, value)
        return "OK"

    if cmd == "GET":
        if len(args) != 1:
            return "ERR wrong number of arguments for GET"
        sentinel = object()
        value = cache.get(args[0], sentinel)
        return "(nil)" if value is sentinel else str(value)

    if cmd == "DEL":
        if len(args) != 1:
            return "ERR wrong number of arguments for DEL"
        return "1" if cache.delete(args[0]) else "0"

    if cmd == "LEN":
        if args:
            return "ERR wrong number of arguments for LEN"
        return str(len(cache))

    if cmd == "STATS":
        if args:
            return "ERR wrong number of arguments for STATS"
        return json.dumps(cache.stats(), sort_keys=True)

    return f"ERR unknown command {tokens[0]!r}"


def run(cache: TTLCache, stdin: TextIO, stdout: TextIO) -> None:
    for line in stdin:
        out = handle_line(cache, line)
        if out is not None:
            stdout.write(out + "\n")
            stdout.flush()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Interactive LRU cache with per-entry TTL."
    )
    parser.add_argument("--maxsize", type=_positive_int, default=128,
                        help="maximum number of entries (default: 128)")
    parser.add_argument("--ttl", type=_positive_float, default=60.0,
                        help="default time-to-live in seconds (default: 60)")
    ns = parser.parse_args(argv)

    try:
        cache = TTLCache(ns.maxsize, ns.ttl)
    except ValueError as exc:
        parser.error(str(exc))  # exits with status 2

    try:
        run(cache, sys.stdin, sys.stdout)
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())

# file: ttlcache.py
"""Thread-safe LRU cache with per-entry time-to-live."""

from __future__ import annotations

import numbers
import threading
import time
from collections import OrderedDict
from typing import Any, Callable

__all__ = ["TTLCache"]


def _valid_ttl(ttl: Any) -> bool:
    return (
        isinstance(ttl, numbers.Real)
        and not isinstance(ttl, bool)
        and ttl > 0  # NaN fails this comparison
    )


class TTLCache:
    """An LRU cache whose entries expire after a time-to-live.

    An entry set at time ``t`` with ttl ``x`` is live while ``clock() < t + x``
    and expired once ``clock() >= t + x``.
    """

    def __init__(
        self,
        maxsize: int,
        ttl: float,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if not isinstance(maxsize, int) or isinstance(maxsize, bool) or maxsize < 1:
            raise ValueError("maxsize must be an int >= 1")
        if not _valid_ttl(ttl):
            raise ValueError("ttl must be a number > 0")
        if not callable(clock):
            raise ValueError("clock must be callable")

        self._maxsize = maxsize
        self._ttl = ttl
        self._clock = clock
        # key -> (value, expires_at); order is LRU (first) -> MRU (last)
        self._data: OrderedDict[Any, tuple[Any, float]] = OrderedDict()
        self._lock = threading.RLock()
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._expirations = 0

    # ----- internal helpers (caller must hold the lock) -----

    def _expire_if_needed(self, key: Any, now: float) -> bool:
        """If ``key`` is present but expired, remove it.

        Returns True if the key is present and live afterwards.
        """
        entry = self._data.get(key)
        if entry is None:
            return False
        if now >= entry[1]:
            del self._data[key]
            self._expirations += 1
            return False
        return True

    def _purge_expired(self, now: float) -> None:
        expired = [k for k, (_, exp) in self._data.items() if now >= exp]
        for k in expired:
            del self._data[k]
        self._expirations += len(expired)

    # ----- public API -----

    def set(self, key: Any, value: Any, ttl: float | None = None) -> None:
        if ttl is None:
            ttl = self._ttl
        elif not _valid_ttl(ttl):
            raise ValueError("ttl must be a number > 0")

        with self._lock:
            now = self._clock()
            if self._expire_if_needed(key, now):
                # Live existing key: replace, reset expiry, mark MRU.
                self._data[key] = (value, now + ttl)
                self._data.move_to_end(key)
                return

            # Inserting a new key.
            if len(self._data) >= self._maxsize:
                self._purge_expired(now)
                if len(self._data) >= self._maxsize:
                    self._data.popitem(last=False)
                    self._evictions += 1
            self._data[key] = (value, now + ttl)

    def get(self, key: Any, default: Any = None) -> Any:
        with self._lock:
            now = self._clock()
            if self._expire_if_needed(key, now):
                self._data.move_to_end(key)
                self._hits += 1
                return self._data[key][0]
            self._misses += 1
            return default

    def delete(self, key: Any) -> bool:
        with self._lock:
            now = self._clock()
            if self._expire_if_needed(key, now):
                del self._data[key]
                return True
            return False

    def __contains__(self, key: Any) -> bool:
        with self._lock:
            return self._expire_if_needed(key, self._clock())

    def __len__(self) -> int:
        with self._lock:
            self._purge_expired(self._clock())
            return len(self._data)

    def stats(self) -> dict:
        with self._lock:
            return {
                "hits": self._hits,
                "misses": self._misses,
                "evictions": self._evictions,
                "expirations": self._expirations,
            }

    def __repr__(self) -> str:
        return f"{type(self).__name__}(maxsize={self._maxsize!r}, ttl={self._ttl!r})"

```

Return ONLY a JSON object (no code fence) of the form {"scores": {"<solution id>": {"spec_fidelity": 1-10, "robustness": 1-10, "readability": 1-10, "maintainability": 1-10, "overall": 1-10, "note": "one sentence naming the most important strength or weakness"}}, "per_task_best": {"<task>": "<solution id>"}}. Score every solution id listed above.