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

Bugs fixed:

1. **Rounding:** `_cents` went through `float` and `round()`, which does not round half up and returned Decimals with binary noise; it now quantizes to `0.01` with `ROUND_HALF_UP`.
2. **Bulk threshold:** the discount used `quantity > 10`; it is now `quantity >= 10`.
3. **Shared state:** the mutable default `lines=[]` was shared across invoices; each invoice now gets its own list, and a list passed in is copied (and validated) rather than aliased.
4. **Tax and coupon order:** tax was computed on the full subtotal and the coupon was applied to subtotal plus tax; the coupon now applies to the subtotal and tax is charged on `subtotal - coupon`.
5. **Fixed coupon cap:** a fixed coupon larger than the subtotal could make the amount negative; it is now capped at the subtotal.
6. **Coupon validation:** bad coupons (non-strings, garbage, NaN/Infinity, percentages outside 0–100, negative amounts) were accepted or raised the wrong exception; they now raise `ValueError` from `apply_coupon`. `apply_coupon(None)` clears the coupon.
7. **Line validation:** non-int quantities (floats, strings, bools) and non-numeric or non-finite prices were accepted or raised the wrong exception; they now raise `ValueError`.
8. **Total consistency:** `total` was rounded separately and could differ by a cent from the other returned values; it is now computed from the rounded components, so `total == subtotal - discount + tax` always holds.
9. **Empty invoice:** `_subtotal()` returned the int `0` for an invoice with no lines; it now returns a Decimal.
10. **Tax rate precision:** a float `tax_rate` such as `0.08` was converted with binary error; it is now converted via `str`, and an unparsable rate raises `ValueError`.

One judgment call: tax is computed on the unrounded `subtotal - coupon` and then rounded, since the docstring only requires rounding of returned amounts. If your spreadsheet computes tax on the already-rounded figures, the tax could differ by a cent in rare cases, and the change is one line in `summary()`.