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

- `_cents` rounded through `float` and Python's banker's rounding. It now uses `Decimal.quantize` with `ROUND_HALF_UP`, which fixes the off-by-one-cent totals.
- The bulk discount condition was `quantity > 10`. It is now `quantity >= 10`, so exactly 10 units gets the discount.
- The mutable default `lines=[]` was shared by every Invoice. The default is now `None`, each invoice gets its own list, and any passed lines are copied and validated.
- The coupon was computed on `subtotal + tax` after tax. It is now applied to the post-bulk subtotal before tax, and tax is charged on `(subtotal - coupon)`.
- A fixed coupon was not capped. It is now capped at the subtotal, so the taxable amount can never go negative.
- Coupons were never validated. Only `"N%"` with N between 0 and 100, or a non-negative plain amount like `"7.50"`, is accepted; anything else raises `ValueError`.
- The quantity check did not require an int. It now rejects floats, bools, strings and values ≤ 0 with `ValueError`.
- An unparseable or non-finite `unit_price` (or tax rate) raised `InvalidOperation`/`TypeError` or slipped through. These now raise `ValueError`.
- `sum()` over an empty invoice returned the int `0`, not a Decimal. It now starts from `Decimal(0)`.
- `total` was rounded on its own and could differ from `subtotal - discount + tax`. It is now computed from the rounded parts, so that identity always holds.