from typing import Annotated

from pydantic import Field

from cosmos.engines.base import BaseEngine
from cosmos.engines.pandas import PandasEngine

Engine = Annotated[
    PandasEngine,
    Field(discriminator="engine"),
]

__all__ = ["PandasEngine", "BaseEngine"]
