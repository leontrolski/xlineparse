# xlineparse

Fast and simple side-by-side diff library for Python - wraps [similar](https://crates.io/crates/similar), inspired by [icdiff](https://github.com/jeffkaufman/icdiff).

# Usage

```shell
pip install xlineparse
```

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
