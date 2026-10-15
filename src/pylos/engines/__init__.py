from typing import Annotated

from pydantic import Field

from pylos.engines.base import BaseEngine
from pylos.engines.pandas import PandasEngine

Engine = Annotated[
    PandasEngine,
    Field(discriminator="engine"),
]

__all__ = ["PandasEngine", "BaseEngine"]
