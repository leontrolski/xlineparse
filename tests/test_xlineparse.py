import datetime as dt
from decimal import Decimal
import enum
from typing import Annotated, Literal
import zoneinfo

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
file_1_schema = xlp.Schema.from_type(
    delimiter="|",
    quote=None,
    trailing_delimiter=False,
    t=AsdLine,
)

QweLine = tuple[
    Literal["qwe"],
    int,
]
file_2_schema = xlp.Schema.from_type(
    delimiter="|",
    quote=None,
    trailing_delimiter=False,
    t=AsdLine | QweLine,
)
file_3_schema = xlp.Schema.from_type(
    delimiter="|",
    quote=None,
    trailing_delimiter=True,
    t=QweLine,
)


class FooEnum(enum.Enum):
    A = "A"
    B = "B"


file_4_schema = xlp.Schema.from_type(
    delimiter="|",
    quote=None,
    trailing_delimiter=False,
    t=tuple[Literal["foo"], FooEnum, FooEnum],
)


def test_parse_line_1() -> None:
    assert file_1_schema.parse_line(
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


def test_parse_line_2() -> None:
    assert file_2_schema.parse_line("qwe|1") == (
        "qwe",
        1,
    )


def test_parse_line_3() -> None:
    assert file_3_schema.parse_line("qwe|1|") == (
        "qwe",
        1,
    )


def test_parse_line_4() -> None:
    assert file_4_schema.parse_line("foo|A|B") == (
        "foo",
        FooEnum.A,
        FooEnum.B,
    )
