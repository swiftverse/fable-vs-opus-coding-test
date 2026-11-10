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

Bugs fixed:

1. `_cents` rounded through `float` and returned an unquantized Decimal; it now quantizes to `0.01` with `ROUND_HALF_UP` (report 1).
2. `total` was rounded independently of its parts, so it could differ by a cent from `subtotal - discount + tax`; it is now computed from the rounded components (report 1).
3. The bulk discount used `quantity > 10`; it is now `>= 10` (report 2).
4. The mutable default `lines=[]` was shared between invoices, and a passed-in list was aliased; each invoice now builds its own list (report 3).
5. Tax was computed on the full subtotal, ignoring the coupon; it is now computed on `subtotal - coupon` (report 4).
6. The percentage coupon was computed on `subtotal + tax`; it is now computed on the subtotal after bulk discounts and before tax (report 4).
7. A fixed coupon was not capped; it is now capped at the subtotal, so the taxable amount and total cannot go negative.
8. Coupons were not validated; percentages outside 0–100, negative amounts, non-numeric text, NaN/Infinity and non-strings now raise `ValueError` in `apply_coupon` (`None` still means no coupon).
9. Quantity was not checked to be an int; non-int quantities (floats, bools, strings) now raise `ValueError`.
10. An unparseable or non-finite `unit_price` leaked `decimal.InvalidOperation`; it now raises `ValueError`.
11. Lines passed to the constructor bypassed validation and Decimal conversion; they now go through `add_line`.
12. `sum()` over an empty invoice returned the int `0` rather than a Decimal; it now starts from `Decimal(0)`.
13. A float `tax_rate` such as `0.08` was converted with its binary error; it is now converted via `str`, and an invalid rate raises `ValueError`.

One interpretation to flag: tax is calculated from the unrounded `subtotal - coupon` and then rounded, since the docstring only says returned amounts are rounded. If your spreadsheet rounds the subtotal and discount first, tax can differ by a cent on lines with sub-cent bulk-discounted totals.