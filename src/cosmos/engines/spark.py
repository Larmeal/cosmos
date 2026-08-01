from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from cosmos.engines.base import BaseEngine

if TYPE_CHECKING:
    from pyspark.sql import DataFrame


class SparkEngine(BaseEngine):
    """Engine class for handling data operations using Spark."""

    engine: Literal["spark"]

    def load_data(self) -> None | DataFrame:
        pass
