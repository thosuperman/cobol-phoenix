import pytest

from phoenix.cobol.picture import PictureError, parse_picture, storage_size


@pytest.mark.parametrize(
    "raw,cat,digits,scale,signed,size",
    [
        ("X(10)", "alphanumeric", 0, 0, False, 10),
        ("S9(7)V99", "numeric", 9, 2, True, 9),
        ("9V9999", "numeric", 5, 4, False, 5),
        ("ZZZ,ZZ9.99-", "numeric-edited", 8, 2, True, 11),
        ("$$$,$$9.99", "numeric-edited", 7, 2, False, 10),
        ("XXBXX", "alphanumeric-edited", 0, 0, False, 5),
    ],
)
def test_picture_parsing(raw, cat, digits, scale, signed, size):
    p = parse_picture(raw)
    assert (p.category, p.digits, p.scale, p.signed, p.size) == (cat, digits, scale, signed, size)


def test_storage_sizes():
    assert storage_size(parse_picture("S9(5)"), "COMP-3", False) == 3
    assert storage_size(parse_picture("S9(4)"), "COMP", False) == 2
    assert storage_size(parse_picture("9(10)"), "COMP", False) == 8
    assert storage_size(parse_picture("S9(3)"), "DISPLAY", True) == 4


def test_invalid_picture():
    with pytest.raises(PictureError):
        parse_picture("X9Z")
