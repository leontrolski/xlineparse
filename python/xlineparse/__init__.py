from typing import TYPE_CHECKING

from . import xlineparse as _xlineparse  # type: ignore

if not TYPE_CHECKING:
    Parser = _xlineparse.Parser
