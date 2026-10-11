from typing import Annotated

from pydantic import Field

from cosmos.engines.base import BaseEngine
from cosmos.engines.pandas import PandasEngine
from cosmos.engines.spark import SparkEngine

Engine = Annotated[
    PandasEngine | SparkEngine,
    Field(discriminator="engine"),
]

__all__ = ["PandasEngine", "SparkEngine", "BaseEngine"]
