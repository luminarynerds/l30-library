import pytest
from app.services.lexile import parse_lexile

@pytest.mark.parametrize(
    "raw,expected",
    [
        ("750L", ("750L", 750)),
        ("750l", ("750L", 750)),
        ("  750L  ", ("750L", 750)),
        ("AD650L", ("AD650L", 650)),
        ("ad650l", ("AD650L", 650)),
        ("HL400L", ("HL400L", 400)),
        ("BR200L", ("BR200L", -200)),
        ("BR", ("BR", 0)),
        ("NP", ("NP", None)),
        ("0L", ("0L", 0)),
        ("1700L", ("1700L", 1700)),
        ("", (None, None)),
        (None, (None, None)),
    ],
)
def test_parse_lexile_valid(raw, expected):
    assert parse_lexile(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "750",
        "L750",
        "750LL",
        "XX500L",
        "AD",
        "abc",
        "2500L",
        "BR500L",
        "-300L",
    ],
)
def test_parse_lexile_invalid(raw):
    with pytest.raises(ValueError):
        parse_lexile(raw)
