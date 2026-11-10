# file: invoice.py
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation

CENT = Decimal("0.01")


def _cents(x):
    return Decimal(x).quantize(CENT, rounding=ROUND_HALF_UP)


class Invoice:
    def __init__(self, tax_rate="0.08", lines=None):
        self.tax_rate = Decimal(str(tax_rate))
        self.lines = list(lines) if lines else []
        self.coupon = None

    def add_line(self, sku, unit_price, quantity):
        unit_price = Decimal(str(unit_price))
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0 or unit_price < 0:
            raise ValueError("bad line")
        self.lines.append((sku, unit_price, quantity))

    def apply_coupon(self, coupon):
        if not isinstance(coupon, str):
            raise ValueError("bad coupon")
        try:
            if coupon.endswith("%"):
                pct = Decimal(coupon[:-1])
                if not (0 <= pct <= 100):
                    raise ValueError("bad coupon")
            else:
                amt = Decimal(coupon)
                if amt < 0:
                    raise ValueError("bad coupon")
        except InvalidOperation:
            raise ValueError("bad coupon")
        if not (pct if coupon.endswith("%") else amt).is_finite():
            raise ValueError("bad coupon")
        self.coupon = coupon

    def _line_total(self, unit_price, quantity):
        total = unit_price * quantity
        if quantity >= 10:
            total = total * Decimal("0.95")
        return total

    def _subtotal(self):
        return sum((self._line_total(p, q) for _, p, q in self.lines), Decimal(0))

    def _coupon_amount(self, subtotal):
        if self.coupon is None:
            return Decimal(0)
        if self.coupon.endswith("%"):
            return subtotal * Decimal(self.coupon[:-1]) / 100
        return min(Decimal(self.coupon), subtotal)

    def summary(self):
        subtotal = _cents(self._subtotal())
        discount = _cents(self._coupon_amount(subtotal))
        tax = _cents((subtotal - discount) * self.tax_rate)
        return {"subtotal": subtotal, "discount": discount, "tax": tax, "total": subtotal - discount + tax}
