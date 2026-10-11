from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, Self

from cosmos.engines.base import BaseEngine

if TYPE_CHECKING:
    from pyspark.sql import DataFrame


class SparkEngine(BaseEngine):
    """Engine class for handling data operations using Spark."""

    engine: Literal["spark"]
    dataframe: DataFrame | None = None

    def is_empty(self) -> bool:
        pass

    def statistics(self) -> dict[str, Any]:
        pass

    def load_data(self, file_path: str | Path) -> Self:
        pass
