from __future__ import annotations

from . import xlineparse as _xlineparse  # type: ignore

from dataclasses import dataclass, replace
import enum
import json
from types import NoneType, UnionType
from typing import Annotated, Any, Literal, Union, get_args, get_origin
import decimal


@dataclass(frozen=True, kw_only=True)
class StrField:
    required: bool = True
    min_length: int | None = None
    max_length: int | None = None
    invalid_characters: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return dict(
            kind="STR",
            required=self.required,
            min_length=self.min_length,
            max_length=self.max_length,
            invalid_characters=self.invalid_characters,
        )


@dataclass(frozen=True, kw_only=True)
class IntField:
    required: bool = True
    min_value: int | None = None
    max_value: int | None = None

    def as_dict(self) -> dict[str, Any]:
        return dict(
            kind="INT",
            required=self.required,
            min_value=self.min_value,
            max_value=self.max_value,
        )


@dataclass(frozen=True, kw_only=True)
class FloatField:
    required: bool = True
    min_value: float | None = None
    max_value: float | None = None

    def as_dict(self) -> dict[str, Any]:
        return dict(
            kind="FLOAT",
            required=self.required,
            min_value=self.min_value,
            max_value=self.max_value,
        )


@dataclass(frozen=True, kw_only=True)
class DecimalField:
    required: bool = True
    max_decimal_places: int | None = None
    min_value: decimal.Decimal | None = None
    max_value: decimal.Decimal | None = None

    def as_dict(self) -> dict[str, Any]:
        return dict(
            kind="DECIMAL",
            required=self.required,
            max_decimal_places=self.max_decimal_places,
            min_value=self.min_value,
            max_value=self.max_value,
        )


@dataclass(frozen=True, kw_only=True)
class BoolField:
    required: bool = True
    true_value: str
    false_value: str  # can only be "" if .required

    def as_dict(self) -> dict[str, Any]:
        return dict(
            kind="BOOL",
            required=self.required,
            true_value=self.true_value,
            false_value=self.false_value,
        )


@dataclass(frozen=True, kw_only=True)
class DatetimeField:
    required: bool = True
    format: str
    time_zone: str  # eg: "UTC" | "Europe/London"

    def as_dict(self) -> dict[str, Any]:
        return dict(
            kind="DATETIME",
            required=self.required,
            format=self.format,
            time_zone=self.time_zone,
        )


@dataclass(frozen=True, kw_only=True)
class DateField:
    required: bool = True
    format: str

    def as_dict(self) -> dict[str, Any]:
        return dict(
            kind="DATE",
            required=self.required,
            format=self.format,
        )


@dataclass(frozen=True, kw_only=True)
class TimeField:
    required: bool = True
    format: str

    def as_dict(self) -> dict[str, Any]:
        return dict(
            kind="TIME",
            required=self.required,
            format=self.format,
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


def field_type_to_field(t: type) -> Field:
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

    if t is str and field is None:
        field = StrField()
    elif t is int and field is None:
        field = IntField()
    elif t is float and field is None:
        field = FloatField()
    elif t is decimal.Decimal and field is None:
        field = DecimalField()
    elif issubclass(t, enum.Enum):
        raise NotImplementedError

    if field is None:
        raise RuntimeError(f"Type {t} needs Annotated[x, XField(...)]")

    field = replace(field, required=required)
    return field


@dataclass(frozen=True, kw_only=True)
class Line:
    name: str
    fields: list[Field]

    def as_dict(self) -> dict[str, Any]:
        return dict(
            name=self.name,
            fields=[field.as_dict() for field in self.fields],
        )


def convert_line_type(t: type) -> Line:
    assert get_origin(t) is tuple
    name_literal, *fields = get_args(t)
    assert get_origin(name_literal) is Literal
    name: str
    (name,) = get_args(name_literal)
    return Line(name=name, fields=[field_type_to_field(t) for t in fields])


@dataclass
class Schema:
    delimiter: str
    quote: str | None
    trailing_delimiter: bool
    lines: list[Line]  # some day, we can use TypeForm here...

    def __post_init__(self) -> None:
        jsonable = dict(
            delimiter=self.delimiter,
            quote=self.quote,
            trailing_delimiter=self.trailing_delimiter,
            lines=[line.as_dict() for line in self.lines],
        )
        self._parser = _xlineparse.Parser(json.dumps(jsonable))

    @staticmethod
    def from_type(
        delimiter: str,
        quote: str | None,
        trailing_delimiter: bool,
        t: Any,
    ) -> Schema:
        if get_origin(t) is Union or get_origin(t) is UnionType:
            lines = [convert_line_type(arg) for arg in get_args(t)]
        else:
            lines = [convert_line_type(t)]
        return Schema(
            delimiter=delimiter,
            quote=quote,
            trailing_delimiter=trailing_delimiter,
            lines=lines,
        )

    def parse_line(self, line: str) -> tuple[Any, ...]:
        return self._parser.parse_line(line)  # type: ignore
