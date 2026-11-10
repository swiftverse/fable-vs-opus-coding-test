from decimal import Decimal as D
import pytest
from invoice import Invoice


@pytest.mark.parametrize("coupon", ["NaN%", "Infinity", "nan", "inf%", "sNaN"])
def test_non_finite_coupons_rejected(coupon):
    inv = Invoice()
    inv.add_line("A", "1.00", 1)
    with pytest.raises(ValueError):
        inv.apply_coupon(coupon)
        inv.summary()


def test_decimal_and_float_prices():
    inv = Invoice(tax_rate="0")
    inv.add_line("A", D("1.10"), 1)
    inv.add_line("B", 0.1, 3)
    assert inv.summary()["subtotal"] == D("1.40")


def test_float_tax_rate_matches_string_tax_rate():
    a, b = Invoice(tax_rate=0.07), Invoice(tax_rate="0.07")
    for inv in (a, b):
        inv.add_line("A", "2.50", 1)
    assert a.summary() == b.summary()


def test_fractional_percent_coupon():
    inv = Invoice(tax_rate="0")
    inv.add_line("A", "200.00", 1)
    inv.apply_coupon("12.5%")
    assert inv.summary()["discount"] == D("25.00")


@pytest.mark.parametrize("price", ["abc", "NaN", "Infinity"])
def test_bad_prices_raise_value_error(price):
    with pytest.raises(ValueError):
        Invoice().add_line("A", price, 1)
