from __future__ import annotations
from collections import defaultdict

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
class StrEnumField:
    required: bool = True
    cls: type[enum.Enum]

    def as_dict(self) -> dict[str, Any]:
        values = {field.value for field in self.cls}
        return dict(
            kind="STR_ENUM",
            required=self.required,
            values=sorted(values),
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
class IntEnumField:
    required: bool = True
    cls: type[enum.Enum]

    def as_dict(self) -> dict[str, Any]:
        values = {field.value for field in self.cls}
        return dict(
            kind="INT_ENUM",
            required=self.required,
            values=sorted(values),
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


def decimal_to_str(d: decimal.Decimal | None) -> str | None:
    if d is None:
        return None
    return f"{d:f}"


@dataclass(frozen=True, kw_only=True)
class DecimalField:
    required: bool = True
    round_decimal_places: int | None = None
    min_value: decimal.Decimal | None = None
    max_value: decimal.Decimal | None = None

    def as_dict(self) -> dict[str, Any]:
        return dict(
            kind="DECIMAL",
            required=self.required,
            round_decimal_places=self.round_decimal_places,
            min_value=decimal_to_str(self.min_value),
            max_value=decimal_to_str(self.max_value),
        )


@dataclass(frozen=True, kw_only=True)
class BoolField:
    required: bool = True
    true_value: str
    false_value: str | None  # can only be "" if .required

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
    | StrEnumField
    | IntField
    | IntEnumField
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
    # Once more in case the Union was nested
    if get_origin(t) is Annotated:
        t, field = get_args(t)

    if t is str and field is None:
        field = StrField()
    elif t is int and field is None:
        field = IntField()
    elif t is float and field is None:
        field = FloatField()
    elif t is decimal.Decimal and field is None:
        field = DecimalField()
    elif issubclass(t, enum.Enum) and field is None:
        if all(isinstance(v.value, str) for v in t):
            field = StrEnumField(cls=t)
        elif all(isinstance(v.value, int) for v in t):
            field = IntEnumField(cls=t)
        else:
            raise NotImplementedError(
                f"Can't convert {t} as all the values are not strings|ints"
            )

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


class LineParseError(ValueError): ...


@dataclass(kw_only=True)
class Schema:
    delimiter: str
    quote_str: str | None = None
    trailing_delimiter: bool = False
    coerce_empty_quoted: bool = False  # convert '""': str|None -> '' instead of None
    lines: list[Line]

    def __post_init__(self) -> None:
        # Add a ._parser
        jsonable = dict(
            delimiter=self.delimiter,
            quote_str=self.quote_str,
            trailing_delimiter=self.trailing_delimiter,
            coerce_empty_quoted=self.coerce_empty_quoted,
            lines=[line.as_dict() for line in self.lines],
        )
        self._parser = _xlineparse.Parser(json.dumps(jsonable))
        # Set up enum conversion map, maybe there's a more efficient way of doing this..
        self._enum_conversions: dict[str, dict[int, StrEnumField | IntEnumField]] = (
            defaultdict(dict)
        )
        for line in self.lines:
            for i, field in enumerate(line.fields, start=1):
                if isinstance(field, (StrEnumField, IntEnumField)):
                    self._enum_conversions[line.name][i] = field

    @staticmethod
    def from_type(
        *,
        delimiter: str,
        quote_str: str | None = None,  # do we quote strings like "foo"
        trailing_delimiter: bool = False,
        coerce_empty_quoted: bool = False,
        t: Any,  # some day, we can use TypeForm here...
    ) -> Schema:
        if get_origin(t) is Union or get_origin(t) is UnionType:
            lines = [convert_line_type(arg) for arg in get_args(t)]
        else:
            lines = [convert_line_type(t)]
        return Schema(
            delimiter=delimiter,
            quote_str=quote_str,
            trailing_delimiter=trailing_delimiter,
            coerce_empty_quoted=coerce_empty_quoted,
            lines=lines,
        )

    def parse_line(self, line: str) -> tuple[Any, ...]:
        try:
            parsed = self._parser.parse_line(line)
        except ValueError as e:
            line = line.rstrip("\n")
            raise LineParseError(f"Failed to parse line: '{line}'\n {e.args[0]}")
        if self._enum_conversions:
            enum_conversion: dict[int, StrEnumField | IntEnumField] = (
                self._enum_conversions[parsed[0]]
            )
            parsed_mut = list(parsed)
            for i, converter in enum_conversion.items():
                v = parsed_mut[i]
                if v is not None:
                    parsed_mut[i] = converter.cls._value2member_map_[v]
            parsed = tuple(parsed_mut)
        return parsed  # type: ignore

    def parse_first(self, line: str) -> str:
        return self._parser.parse_first(line)  # type: ignore
