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

schema = xlp.Schema.from_type(
    delimiter="|",
    quote_str=None,
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

- Refactor some of the `is_none()`s with a bit o' ChatGPT.
- Allow delimiters to be escaped.
- Test errors.
- `IntEnum`
- Can we make enums quicker?

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
