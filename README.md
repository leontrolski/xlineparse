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

AsdLine = tuple[
    Literal["asd"],
    int,
    Decimal,
    Decimal | None,
    Annotated[bool, xlp.BoolField(true_value="Y", false_value="F")],
    Annotated[dt.date, xlp.DateField(format="%Y-%m-%d")],
    Annotated[dt.time, xlp.TimeField(format="%H%M%s")],
]
QweLine = tuple[
    Literal["qwe"],
    int,
]

schema = xlp.Schema(
    delimiter="|",
    quote=None,
    trailing_delimiter=False,
    lines=AsdLine | QweLine,
)

schema.parse_line("asd|1|3.14||Y|2012-01-02|123200")

#  Will return:

(
    "asd",
    1,
    Decimal("3.14"),
    None,
    True,
    dt.date(2012, 1, 2),
    dt.time(12, 32, 0),
)
```

# TODO:

- Implement Enum.
- Implement constraints:
    - StrField.min_length
    - StrField.max_length
    - StrField.invalid_characters
    - IntField.min_value: int | None = None
    - IntField.max_value: int | None = None
    - FloatField.min_value: float | None = None
    - FloatField.max_value: float | None = None
    - DecimalField.max_decimal_places: int | None = None
    - DecimalField.min_value: decimal.Decimal | None = None
    - DecimalField.max_value: decimal.Decimal | None = None
- Implement different quote characters.
- Allow delimiters to be escaped.
- Refactor some of the `is_none()`s with a bit o' ChatGPT.

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
