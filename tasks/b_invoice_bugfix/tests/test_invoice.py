from decimal import Decimal as D
import pytest
from invoice import Invoice


def test_simple_invoice_with_tax():
    inv = Invoice(tax_rate="0.08")
    inv.add_line("A", "10.00", 2)
    inv.add_line("B", "5.25", 1)
    s = inv.summary()
    assert s == {"subtotal": D("25.25"), "discount": D("0.00"), "tax": D("2.02"), "total": D("27.27")}


def test_returned_values_are_decimals_quantized_to_cents():
    inv = Invoice()
    inv.add_line("A", "1", 1)
    s = inv.summary()
    for k in ("subtotal", "discount", "tax", "total"):
        assert isinstance(s[k], D)
        assert s[k].as_tuple().exponent == -2


def test_half_up_rounding_not_bankers():
    # 0.125 must round to 0.13 (half up). float/banker's rounding gives 0.12.
    inv = Invoice(tax_rate="0")
    inv.add_line("A", "0.125", 1)
    assert inv.summary()["subtotal"] == D("0.13")


def test_half_up_rounding_on_tax():
    # 2.50 * 0.07 = 0.175 -> 0.18 with ROUND_HALF_UP
    inv = Invoice(tax_rate="0.07")
    inv.add_line("A", "2.50", 1)
    s = inv.summary()
    assert s["tax"] == D("0.18")
    assert s["total"] == D("2.68")


def test_float_artifact_rounding():
    # 1.005 is 1.00499999... as a float; Decimal half-up gives 1.01
    inv = Invoice(tax_rate="0")
    inv.add_line("A", "1.005", 1)
    assert inv.summary()["subtotal"] == D("1.01")


def test_bulk_discount_at_exactly_ten():
    inv = Invoice(tax_rate="0")
    inv.add_line("A", "10.00", 10)
    assert inv.summary()["subtotal"] == D("95.00")


def test_no_bulk_discount_at_nine():
    inv = Invoice(tax_rate="0")
    inv.add_line("A", "10.00", 9)
    assert inv.summary()["subtotal"] == D("90.00")


def test_bulk_discount_is_per_line():
    inv = Invoice(tax_rate="0")
    inv.add_line("A", "1.00", 10)
    inv.add_line("B", "1.00", 5)
    assert inv.summary()["subtotal"] == D("14.50")


def test_invoices_are_independent():
    a = Invoice()
    a.add_line("A", "1.00", 1)
    b = Invoice()
    assert b.summary()["subtotal"] == D("0.00")
    b.add_line("B", "2.00", 1)
    assert a.summary()["subtotal"] == D("1.00")
    assert b.summary()["subtotal"] == D("2.00")


def test_percent_coupon_applies_before_tax():
    inv = Invoice(tax_rate="0.10")
    inv.add_line("A", "100.00", 1)
    inv.apply_coupon("15%")
    s = inv.summary()
    assert s["subtotal"] == D("100.00")
    assert s["discount"] == D("15.00")
    assert s["tax"] == D("8.50")
    assert s["total"] == D("93.50")


def test_fixed_coupon_applies_before_tax():
    inv = Invoice(tax_rate="0.10")
    inv.add_line("A", "40.00", 1)
    inv.apply_coupon("7.50")
    s = inv.summary()
    assert s == {"subtotal": D("40.00"), "discount": D("7.50"), "tax": D("3.25"), "total": D("35.75")}


def test_fixed_coupon_capped_at_subtotal():
    inv = Invoice(tax_rate="0.10")
    inv.add_line("A", "5.00", 1)
    inv.apply_coupon("20")
    s = inv.summary()
    assert s["discount"] == D("5.00")
    assert s["tax"] == D("0.00")
    assert s["total"] == D("0.00")


def test_coupon_after_bulk_discount():
    inv = Invoice(tax_rate="0")
    inv.add_line("A", "10.00", 10)  # 95.00 after bulk
    inv.apply_coupon("10%")
    s = inv.summary()
    assert s["discount"] == D("9.50")
    assert s["total"] == D("85.50")


def test_total_identity_holds():
    inv = Invoice(tax_rate="0.0825")
    inv.add_line("A", "19.99", 3)
    inv.add_line("B", "0.333", 12)
    inv.apply_coupon("12.5%")
    s = inv.summary()
    assert s["total"] == s["subtotal"] - s["discount"] + s["tax"]


@pytest.mark.parametrize("coupon", ["abc", "101%", "-5%", "%", "ten", ""])
def test_invalid_coupon_raises(coupon):
    inv = Invoice()
    inv.add_line("A", "1.00", 1)
    with pytest.raises(ValueError):
        inv.apply_coupon(coupon)
        inv.summary()


@pytest.mark.parametrize("coupon", ["0%", "100%"])
def test_boundary_percent_coupons_ok(coupon):
    inv = Invoice(tax_rate="0")
    inv.add_line("A", "10.00", 1)
    inv.apply_coupon(coupon)
    s = inv.summary()
    assert s["total"] == (D("10.00") if coupon == "0%" else D("0.00"))


@pytest.mark.parametrize("price,qty", [("1.00", 0), ("1.00", -1), ("-0.01", 1)])
def test_invalid_lines_raise(price, qty):
    with pytest.raises(ValueError):
        Invoice().add_line("A", price, qty)
