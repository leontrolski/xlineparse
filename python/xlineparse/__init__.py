from . import xlineparse as _xlineparse  # type: ignore

from dataclasses import dataclass
import datetime as dt
import enum
import json
from types import NoneType, UnionType
from typing import Annotated, Any, Literal, TypedDict, Union, get_args, get_origin
import decimal


class _StrField(TypedDict):
    kind: Literal["STR"]
    required: bool
    min_length: int | None
    max_length: int | None
    invalid_characters: str | None


class _IntField(TypedDict):
    kind: Literal["INT"]
    required: bool
    min_value: int | None
    max_value: int | None


class _FloatField(TypedDict):
    kind: Literal["FLOAT"]
    required: bool
    min_value: float | None
    max_value: float | None


class _DecimalField(TypedDict):
    kind: Literal["DECIMAL"]
    required: bool
    max_decimal_places: int | None
    min_value: decimal.Decimal | None
    max_value: decimal.Decimal | None


class _BoolField(TypedDict):
    kind: Literal["BOOL"]
    required: bool
    true_value: str
    false_value: str  # can only be "" if .required


class _EnumField(TypedDict):
    kind: Literal["ENUM"]
    required: bool
    values: list[str]


class _DatetimeField(TypedDict):
    kind: Literal["DATETIME"]
    required: bool
    format: str
    time_zone: str  # eg: "UTC" | "Europe/London"


class _DateField(TypedDict):
    kind: Literal["DATE"]
    required: bool
    format: str


class _TimeField(TypedDict):
    kind: Literal["TIME"]
    required: bool
    format: str


@dataclass(frozen=True)
class StrField:
    min_length: int | None = None
    max_length: int | None = None
    invalid_characters: str | None = None


@dataclass(frozen=True)
class IntField:
    min_value: int | None = None
    max_value: int | None = None


@dataclass(frozen=True)
class FloatField:
    min_value: float | None = None
    max_value: float | None = None


@dataclass(frozen=True)
class DecimalField:
    max_decimal_places: int | None = None
    min_value: decimal.Decimal | None = None
    max_value: decimal.Decimal | None = None


@dataclass(frozen=True)
class BoolField:
    true_value: str
    false_value: str  # can only be "" if .required


@dataclass(frozen=True)
class DatetimeField:
    format: str
    time_zone: str  # eg: "UTC" | "Europe/London"


@dataclass(frozen=True)
class DateField:
    format: str


@dataclass(frozen=True)
class TimeField:
    format: str


_Field = (
    _StrField
    | _IntField
    | _FloatField
    | _DecimalField
    | _BoolField
    | _EnumField
    | _DatetimeField
    | _DateField
    | _TimeField
)
Field = (
    StrField
    | IntField
    | FloatField
    | DecimalField
    | BoolField
    | DatetimeField
    | DateField
    | TimeField
)


def field_type_to_dict(t: type) -> _Field:
    field: Field | None = None
    required = True
    if get_origin(t) is Annotated:
        t, field = get_args(t)
    if get_origin(t) is Union or get_origin(t) is UnionType:
        args = set(get_args(t))
        assert len(args) == 2
        args -= {None, NoneType}
        (t,) = args
        required = False

    if t is str:
        if field is None:
            field = StrField()
        assert isinstance(field, StrField)
        return _StrField(
            kind="STR",
            required=required,
            min_length=field.min_length,
            max_length=field.max_length,
            invalid_characters=field.invalid_characters,
        )
    elif t is int:
        if field is None:
            field = IntField()
        assert isinstance(field, IntField)
        return _IntField(
            kind="INT",
            required=required,
            min_value=field.min_value,
            max_value=field.max_value,
        )
    elif t is float:
        if field is None:
            field = FloatField()
        assert isinstance(field, FloatField)
        return _FloatField(
            kind="FLOAT",
            required=required,
            min_value=field.min_value,
            max_value=field.max_value,
        )
    elif t is decimal.Decimal:
        if field is None:
            field = DecimalField()
        assert isinstance(field, DecimalField)
        return _DecimalField(
            kind="DECIMAL",
            required=required,
            max_decimal_places=field.max_decimal_places,
            min_value=field.min_value,
            max_value=field.max_value,
        )
    elif t is bool:
        assert isinstance(field, BoolField)
        return _BoolField(
            kind="BOOL",
            required=required,
            true_value=field.true_value,
            false_value=field.false_value,
        )
    elif issubclass(t, enum.Enum):
        raise NotImplementedError
        return _EnumField(
            kind="ENUM",
            required=required,
            values=[],
        )
    elif t is dt.datetime:
        assert isinstance(field, DatetimeField)
        return _DatetimeField(
            kind="DATETIME",
            required=required,
            format=field.format,
            time_zone=field.time_zone,
        )
    elif t is dt.date:
        assert isinstance(field, DateField)
        return _DateField(
            kind="DATE",
            required=required,
            format=field.format,
        )
    elif t is dt.time:
        assert isinstance(field, TimeField)
        return _TimeField(
            kind="TIME",
            required=required,
            format=field.format,
        )
    else:
        raise RuntimeError(f"Unknown type: {t}")


def line_types_to_dict(t: type) -> dict[Any, Any]:
    assert get_origin(t) is tuple
    name_literal, *fields = get_args(t)
    assert get_origin(name_literal) is Literal
    name: str
    (name,) = get_args(name_literal)
    return dict(name=name, fields=[field_type_to_dict(t) for t in fields])


def lines_types_to_dict(t: Any) -> list[Any]:
    if get_origin(t) is Union or get_origin(t) is UnionType:
        return [line_types_to_dict(arg) for arg in get_args(t)]
    return [line_types_to_dict(t)]


@dataclass
class Schema:
    delimiter: str
    quote: str | None
    trailing_delimiter: bool
    lines: Any  # some day, we can use TypeForm here...

    def __post_init__(self) -> None:
        lines = lines_types_to_dict(self.lines)
        jsonable = dict(
            delimiter=self.delimiter,
            quote=self.quote,
            trailing_delimiter=self.trailing_delimiter,
            lines=lines,
        )
        self._parser = _xlineparse.Parser(json.dumps(jsonable))

    def parse_line(self, line: str) -> tuple[Any, ...]:
        return self._parser.parse_line(line)  # type: ignore
