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
