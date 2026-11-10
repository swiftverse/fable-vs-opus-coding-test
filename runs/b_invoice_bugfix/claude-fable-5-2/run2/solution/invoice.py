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
