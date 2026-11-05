"""COBOL semantics of phoenix_runtime. Expected values were confirmed with GnuCOBOL 3.2."""

from decimal import Decimal as D

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from phoenix.codegen import phoenix_runtime as rt


def num(digits, scale=0, signed=False, **kw):
    region = rt.Region("R", digits + 2)
    return rt.Numeric(region, 0, digits + (1 if kw.get("sign_separate") else 0), "N", digits=digits, scale=scale, signed=signed, **kw)


def test_store_truncates_and_rounds_half_away_from_zero():
    f = num(5, 2)
    f.store(D(2) / D(3))
    assert f.value == D("0.66")
    f.store(D(2) / D(3), rounded=True)
    assert f.value == D("0.67")
    g = num(5, 2, signed=True)
    g.store(D("-2.675"), rounded=True)
    assert g.value == D("-2.68")


def test_high_order_truncation_and_size_error():
    f = num(3)
    f.store(D(1234))
    assert f.value == D(234)
    assert f.store(D(5678), size_error=True) is False and f.value == D(234)


def test_unsigned_receiver_stores_absolute_value():
    f = num(3, 2)
    f.store(D("-2.675"), rounded=True)
    assert f.value == D("2.68")


def test_sign_overpunch_and_separate_sign_bytes():
    f = num(3, signed=True)
    f.store(D(-12))
    assert f.raw() == b"01r" and f.display_text() == "-012"
    f.store(D(12))
    assert f.display_text() == "+012"
    s = num(3, signed=True, sign_separate=True, sign_leading=True)
    s.store(D(-5))
    assert s.raw() == b"-005"


def test_packed_and_binary():
    r = rt.Region("R", 8)
    p = rt.Packed(r, 0, 3, "P", digits=5, signed=True)
    p.store(D(-123))
    assert p.raw() == bytes([0x00, 0x12, 0x3D]) and p.value == D(-123)
    b = rt.Binary(r, 4, 2, "B", digits=4, signed=True)
    b.store(D(12345))  # binary truncation to PICTURE digits
    assert b.value == D(2345)


@pytest.mark.parametrize(
    "pic,value,expected",
    [
        ("ZZZ,ZZ9.99-", "-1234.5", "  1,234.50-"),
        ("$$$,$$9.99", "1234.5", " $1,234.50"),
        ("$$$,$$9.99", "104059.41", "$04,059.41"),
        ("-99999.99", "-12.345", "-00012.34"),
        ("ZZZZ9", "0", "    0"),
        ("ZZZ.ZZ", "0", "      "),
    ],
)
def test_numeric_editing_matches_gnucobol(pic, value, expected):
    from phoenix.cobol.picture import parse_picture

    p = parse_picture(pic)
    r = rt.Region("R", p.size)
    e = rt.Edited(r, 0, p.size, "E", digits=p.digits, scale=p.scale, signed=p.signed, picture=p.expanded)
    e.store(D(value))
    assert e.text() == expected


def test_alphanumeric_moves():
    r = rt.Region("R", 20)
    x = rt.Alnum(r, 0, 5, "X")
    rt.move("ABCDEFG", x)
    assert x.text() == "ABCDE"
    rt.move("AB", x)
    assert x.text() == "AB   "
    n = rt.Numeric(r, 5, 5, "N", digits=5)
    rt.move("12A", n)  # GnuCOBOL runtime path for an alphanumeric *field*
    assert n.text() == "00012"
    m = rt.Numeric(r, 10, 7, "M", digits=7, scale=2)
    rt.move("12.5", m)
    assert m.value == D("12.50")
    rt.move(rt.ZEROS, x)
    assert x.text() == "00000"


def test_comparisons_follow_cobol_rules():
    r = rt.Region("R", 10)
    x = rt.Alnum(r, 0, 4, "X")
    rt.move("AB", x)
    assert rt.cmp(x, "AB") == 0  # shorter operand padded with spaces
    assert rt.cmp(x, rt.SPACES) > 0
    n = rt.Numeric(r, 4, 3, "N", digits=3)
    n.store(D(7))
    assert rt.cmp(n, rt.lit("7.0")) == 0 and rt.cmp(n, rt.ZEROS) > 0


def test_initialize_and_string():
    r = rt.Region("R", 12)
    g = rt.Group(r, 0, 12, "G")
    a = rt.Alnum(r, 0, 4, "A")
    n = rt.Numeric(r, 4, 3, "N", digits=3)
    f = rt.Alnum(r, 7, 5, "F", filler=True)
    g.children = [a, n, f]
    r.buf[:] = b"XXXXYYYZZZZZ"
    rt.initialize(g)
    assert r.buf == bytearray(b"    000ZZZZZ")  # FILLER untouched
    out = rt.Alnum(rt.Region("O", 10), 0, 10, "O")
    over = rt.string_into(out, [("AB", None), ("CD-EF", "-"), (rt.lit("12"), None)])
    assert out.text() == "ABCD12    " and not over


def test_intrinsic_dates():
    assert rt.fn("INTEGER-OF-DATE", rt.lit("16010101")) == D(1)
    assert rt.fn("DATE-OF-INTEGER", rt.fn("INTEGER-OF-DATE", rt.lit("20240324")) + 3650) == D(20340322)
    assert rt.fn("INTEGER-OF-DATE", rt.lit("20240324")) == D(154581)  # GnuCOBOL output


@settings(max_examples=300, derandomize=True)
@given(st.decimals(min_value=D("-99999.99"), max_value=D("99999.99"), places=2, allow_nan=False, allow_infinity=False))
def test_property_signed_display_roundtrip(v):
    f = num(7, 2, signed=True)
    f.store(v)
    assert f.value == v
    assert isinstance(f.value, D)


@settings(max_examples=300, derandomize=True)
@given(st.decimals(min_value=D("-9999.9999"), max_value=D("9999.9999"), places=4, allow_nan=False, allow_infinity=False))
def test_property_rounding_is_symmetric_half_away_from_zero(v):
    a = num(7, 2, signed=True)
    b = num(7, 2, signed=True)
    a.store(v, rounded=True)
    b.store(-v, rounded=True)
    assert a.value == -b.value
    assert abs(a.value - v) <= D("0.005")


@settings(max_examples=200, derandomize=True)
@given(st.decimals(min_value=D(0), max_value=D("99999.999"), places=3, allow_nan=False, allow_infinity=False))
def test_property_packed_roundtrip(v):
    r = rt.Region("R", 4)
    p = rt.Packed(r, 0, 4, "P", digits=7, scale=2, signed=False)
    p.store(v)
    assert p.value == v.quantize(D("0.01"), rounding="ROUND_DOWN")
