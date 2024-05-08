# xlineparse

Python library to parse variable length delimited lines.

# Usage

```shell
pip install xlineparse
```

```python
import datetime as dt
from decimal import Decimal
from typing import Annotated, Literal

import xlineparse as xlp

FooLine = tuple[
    Literal["foo"],
    int,
    Decimal,
    Decimal | None,
    Annotated[bool, xlp.BoolField(true_value="Y", false_value="F")],
    Annotated[dt.date, xlp.DateField(format="%Y-%m-%d")],
    Annotated[dt.time, xlp.TimeField(format="%H%M%s")],
]
BarLine = tuple[
    Literal["bar"],
    int,
]
schema = xlp.Schema.from_type(
    delimiter="|",
    quote_str=None,
    trailing_delimiter=False,
    lines=FooLine | BarLine,
)

schema.parse_line("foo|1|3.14||Y|2012-01-02|123200")

#  Will return:

(
    "foo",
    1,
    Decimal("3.14"),
    None,
    True,
    dt.date(2012, 1, 2),
    dt.time(12, 32, 0),
)
```

Or directly construct `Field`s:

```python
schema = xlp.Schema(
    delimiter="|",
    quote_str=None,
    trailing_delimiter=False,
    lines=[
        xlp.Line(
            name="a",
            fields=[
                xlp.DecimalField(
                    required=True,
                    max_decimal_places=None,
                    min_value=Decimal("2.0"),
                    max_value=None,
                )
            ],
        )
    ],
)
assert schema.parse_line("a|2.0")

#  Will return:

("a", Decimal("2.0"))
```

# TODO:

- Allow delimiters to be escaped.
- `IntEnum`
- Can we make enums quicker by moving to Rust?

# Install/Develop

```shell
uv pip install -e '.[dev]'
maturin develop
```

# Make release

- Add pypi token and user = `__token__` to settings (do this once).
- Upversion `pyproject.toml`.

```shell
git tag -a v0.0.x head -m v0.0.x
git push origin v0.0.x
```
