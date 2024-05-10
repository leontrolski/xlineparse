import datetime as dt
from decimal import Decimal
import enum
from typing import Annotated, Any, Literal
import zoneinfo

import pytest
import xlineparse as xlp

AsdLine = tuple[
    Literal["asd"],
    int,
    Decimal,
    Decimal | None,
    Annotated[bool, xlp.BoolField(true_value="Y", false_value="F")],
    Annotated[dt.date, xlp.DateField(format="%Y-%m-%d")],
    Annotated[dt.time, xlp.TimeField(format="%H%M%s")],
    Annotated[
        dt.datetime, xlp.DatetimeField(format="%Y-%m-%d %H:%M:%S", time_zone="UTC")
    ],
    Annotated[
        dt.datetime,
        xlp.DatetimeField(format="%Y-%m-%d %H:%M:%S", time_zone="Europe/London"),
    ],
]
schema_many_types = xlp.Schema.from_type(
    delimiter="|",
    t=AsdLine,
)

QweLine = tuple[
    Literal["qwe"],
    int,
]


class FooEnum(enum.Enum):
    A = "A"
    B = "B"


class WeirdQuotedEnum(enum.Enum):
    A = '"A"'
    B = '"B"'


class BarEnum(enum.Enum):
    ONE = 1
    TWO = 2


def test_parse_types() -> None:
    assert schema_many_types.parse_line(
        "asd|1|3.14||Y|2012-01-02|123200|2014-07-28 12:00:09|2014-07-28 12:00:09"
    ) == (
        "asd",
        1,
        Decimal("3.14"),
        None,
        True,
        dt.date(2012, 1, 2),
        dt.time(12, 32, 0),
        dt.datetime(2014, 7, 28, 12, 0, 9, tzinfo=dt.timezone.utc),
        dt.datetime(2014, 7, 28, 12, 0, 9, tzinfo=zoneinfo.ZoneInfo("Europe/London")),
    )


def test_parse_either_line() -> None:
    assert xlp.Schema.from_type(
        delimiter="|",
        t=AsdLine | QweLine,
    ).parse_line("qwe|1") == (
        "qwe",
        1,
    )


def test_parse_trailing() -> None:
    assert xlp.Schema.from_type(
        delimiter="|",
        trailing_delimiter=True,
        t=QweLine,
    ).parse_line("qwe|1|\n") == (
        "qwe",
        1,
    )


def test_parse_trailing_many() -> None:
    assert xlp.Schema.from_type(
        delimiter="|",
        trailing_delimiter=True,
        t=tuple[Literal["a"], int | None, int | None],
    ).parse_line("a|||") == (
        "a",
        None,
        None,
    )


def test_parse_str_enum() -> None:
    schema = xlp.Schema.from_type(
        delimiter="|",
        t=tuple[Literal["foo"], FooEnum, FooEnum | None],
    )
    assert schema.parse_line("foo|A|B") == (
        "foo",
        FooEnum.A,
        FooEnum.B,
    )
    assert schema.parse_line("foo|A|") == (
        "foo",
        FooEnum.A,
        None,
    )


def test_parse_str_enum_weird_quoted() -> None:
    schema = xlp.Schema.from_type(
        delimiter="|",
        quote_str='"',
        t=tuple[Literal["foo"], WeirdQuotedEnum],
    )
    assert schema.parse_line("foo|A") == (
        "foo",
        WeirdQuotedEnum.A,
    )


def test_parse_int_enum() -> None:
    assert xlp.Schema.from_type(
        delimiter="|",
        t=tuple[Literal["bar"], BarEnum],
    ).parse_line("bar|2") == (
        "bar",
        BarEnum.TWO,
    )


def test_parse_quoted() -> None:
    assert xlp.Schema.from_type(
        delimiter=",",
        quote_str='"',
        t=tuple[Literal["zxc"], str, int],
    ).parse_line('"zxc","oi oi",4') == (
        "zxc",
        "oi oi",
        4,
    )


def test_parse_quoted_weird_bool() -> None:
    assert xlp.Schema.from_type(
        delimiter=",",
        quote_str='"',
        t=tuple[
            Literal["zxc"],
            Annotated[bool, xlp.BoolField(true_value='"Y"', false_value="")],
        ],
    ).parse_line('"zxc",Y') == (
        "zxc",
        True,
    )


def test_parse_quoted_missing() -> None:
    assert xlp.Schema.from_type(
        delimiter=",",
        quote_str='"',
        t=tuple[Literal["zxc"], str, int],
    ).parse_line('"zxc",oi oi,4') == (
        "zxc",
        "oi oi",
        4,
    )


def test_parse_quoted_with_comma() -> None:
    assert xlp.Schema.from_type(
        delimiter=",",
        quote_str='"',
        t=tuple[Literal["zxc"], str, int],
    ).parse_line('"zxc","oi, oi",4') == (
        "zxc",
        "oi, oi",
        4,
    )


def test_emptyness() -> None:
    assert xlp.Schema.from_type(
        delimiter="|",
        t=tuple[Literal["a"], str],
    ).parse_line(
        "a|"
    ) == ("a", "")
    assert xlp.Schema.from_type(
        delimiter="|",
        t=tuple[Literal["a"], str | None],
    ).parse_line("a|") == ("a", None)
    assert xlp.Schema.from_type(
        delimiter=",",
        quote_str='"',
        t=tuple[Literal["a"], str | None],
    ).parse_line('"a",') == ("a", None)
    assert xlp.Schema.from_type(
        delimiter=",",
        quote_str='"',
        t=tuple[Literal["a"], str],
    ).parse_line('"a",""') == ("a", "")
    assert xlp.Schema.from_type(
        delimiter=",",
        quote_str='"',
        t=tuple[Literal["a"], str | None],
    ).parse_line('"a",""') == ("a", None)
    assert xlp.Schema.from_type(
        delimiter=",",
        quote_str='"',
        coerce_empty_quoted=True,
        t=tuple[Literal["a"], str | None],
    ).parse_line('"a",""') == ("a", "")


def _simple_schema(t: Any) -> xlp.Schema:
    return xlp.Schema.from_type(
        delimiter="|",
        t=tuple[Literal["a"], t],
    )


def test_str_constraints() -> None:
    _simple_schema(Annotated[str, xlp.StrField(min_length=2)]).parse_line("a|hi")
    with pytest.raises(xlp.LineParseError):
        _simple_schema(Annotated[str, xlp.StrField(min_length=2)]).parse_line("a|i")

    _simple_schema(Annotated[str, xlp.StrField(max_length=2)]).parse_line("a|hi")
    with pytest.raises(xlp.LineParseError):
        _simple_schema(Annotated[str, xlp.StrField(max_length=2)]).parse_line("a|hii")

    _simple_schema(Annotated[str, xlp.StrField(invalid_characters="abc")]).parse_line(
        "a|def"
    )
    with pytest.raises(xlp.LineParseError):
        _simple_schema(
            Annotated[str, xlp.StrField(invalid_characters="abc")]
        ).parse_line("a|decf")


def test_int_constraints() -> None:
    _simple_schema(Annotated[int, xlp.IntField(min_value=2)]).parse_line("a|2")
    with pytest.raises(xlp.LineParseError):
        _simple_schema(Annotated[int, xlp.IntField(min_value=2)]).parse_line("a|1")

    _simple_schema(Annotated[int, xlp.IntField(max_value=2)]).parse_line("a|2")
    with pytest.raises(xlp.LineParseError):
        _simple_schema(Annotated[int, xlp.IntField(max_value=2)]).parse_line("a|3")


def test_float_constraints() -> None:
    _simple_schema(Annotated[float, xlp.FloatField(min_value=2.0)]).parse_line("a|2.0")
    with pytest.raises(xlp.LineParseError):
        _simple_schema(Annotated[float, xlp.FloatField(min_value=2.0)]).parse_line(
            "a|1.0"
        )

    _simple_schema(Annotated[float, xlp.FloatField(max_value=2.0)]).parse_line("a|2.0")
    with pytest.raises(xlp.LineParseError):
        _simple_schema(Annotated[float, xlp.FloatField(max_value=2.0)]).parse_line(
            "a|3.0"
        )


def test_decimal_constraints() -> None:
    _simple_schema(
        Annotated[Decimal, xlp.DecimalField(min_value=Decimal("2.0"))]
    ).parse_line("a|2.0")
    with pytest.raises(xlp.LineParseError):
        _simple_schema(
            Annotated[Decimal, xlp.DecimalField(min_value=Decimal("2.0"))]
        ).parse_line("a|1.0")

    _simple_schema(
        Annotated[Decimal, xlp.DecimalField(max_value=Decimal("2.0"))]
    ).parse_line("a|2.0")
    with pytest.raises(xlp.LineParseError):
        _simple_schema(
            Annotated[Decimal, xlp.DecimalField(max_value=Decimal("2.0"))]
        ).parse_line("a|3.0")


def test_decimal_rounding() -> None:
    assert _simple_schema(
        Annotated[Decimal, xlp.DecimalField(round_decimal_places=3)]
    ).parse_line("a|2.000") == ("a", Decimal("2.000"))
    assert _simple_schema(
        Annotated[Decimal, xlp.DecimalField(round_decimal_places=3)]
    ).parse_line("a|2.00001") == ("a", Decimal("2.000"))


def test_errors() -> None:
    xlp.Schema.from_type(
        delimiter="|",
        t=tuple[Literal["a"], int],
    ).parse_line("a|1")

    with pytest.raises(xlp.LineParseError):
        xlp.Schema.from_type(
            delimiter="||",  # too long
            t=tuple[Literal["a"], int],
        ).parse_line("a|1")

    with pytest.raises(xlp.LineParseError):
        xlp.Schema.from_type(
            delimiter="|",
            quote_str='""',  # too long
            t=tuple[Literal["a"], int],
        ).parse_line("a|1")

    with pytest.raises(xlp.LineParseError):
        xlp.Schema.from_type(
            delimiter="|",
            trailing_delimiter=True,  # no trailing
            t=tuple[Literal["a"], int],
        ).parse_line("a|1")

    with pytest.raises(xlp.LineParseError):
        xlp.Schema.from_type(
            delimiter="|",
            t=tuple[Literal["a"], int],
        ).parse_line(
            "a|1|2"
        )  # too many parts


def test_low_level_usage() -> None:
    schema = xlp.Schema(
        delimiter="|",
        lines=[
            xlp.Line(
                name="a",
                fields=[
                    xlp.DecimalField(
                        required=True,
                        round_decimal_places=None,
                        min_value=Decimal("2.0"),
                        max_value=None,
                    )
                ],
            )
        ],
    )
    assert schema.parse_line("a|2.0") == ("a", Decimal("2.0"))


def test_big_decimal() -> None:
    schema = xlp.Schema(
        delimiter="|",
        lines=[
            xlp.Line(
                name="a",
                fields=[
                    xlp.DecimalField(
                        required=True,
                        round_decimal_places=None,
                        min_value=Decimal("0"),
                        max_value=Decimal("1E+28"),
                    )
                ],
            )
        ],
    )
    assert schema.parse_line("a|2.0") == ("a", Decimal("2.0"))


def test_weird_time() -> None:
    schema = xlp.Schema(
        delimiter="|",
        lines=[
            xlp.Line(
                name="a",
                fields=[xlp.TimeField(required=True, format="%H%M%S")],
            )
        ],
    )
    assert schema.parse_line("a|240000") == ("a", dt.time(0, 0, 0))


def test_parse_first() -> None:
    assert (
        xlp.Schema.from_type(
            delimiter="|",
            t=tuple[Literal["a"], str | None],
        ).parse_first("abc|bkaaadfsd|sdfsdf")
        == "abc"
    )
    assert (
        xlp.Schema.from_type(
            delimiter=",",
            quote_str='"',
            t=tuple[Literal["a"], str | None],
        ).parse_first('"abc"...bkaaadfsd')
        == "abc"
    )
    assert (
        xlp.Schema.from_type(
            delimiter=",",
            quote_str='"',
            t=tuple[Literal["a"], str | None],
        ).parse_first("abc,...bkaaadfsd")
        == "abc"
    )
