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
