from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Literal, Self

import pandas as pd

from cosmos.engines.base import BaseEngine
from cosmos.exceptions.data_error import SourceEmptyError

logger = logging.getLogger(__name__)


class PandasEngine(BaseEngine):
    """Engine class for handling data operations using pandas."""

    engine: Literal["pandas"]
    dataframe: pd.DataFrame | None = None

    def is_empty(self) -> bool:
        return self.dataframe.empty if self.dataframe is not None else True

    def statistics(self) -> dict[str, Any]:
        assert self.dataframe is not None
        return {
            "row_count": self.dataframe.shape[0],
            "column_count": self.dataframe.shape[1],
            "columns": self.dataframe.columns.tolist(),
        }

    def load_data(self, file_path: str | Path) -> Self:
        logger.debug("loading %s as %s with options %s", file_path, self.source.file_format, self.source.options)

        match self.source.file_format:
            case "csv":
                try:
                    self.dataframe = pd.read_csv(file_path, **self.source.options)
                except pd.errors.EmptyDataError as e:
                    raise SourceEmptyError(f"{file_path} has no content to read") from e
            case _:
                raise ValueError(f"Unsupported source type: {self.source.file_format}")

        assert self.dataframe is not None
        logger.info("loaded %s: %d row(s), %d column(s)", file_path, self.dataframe.shape[0], self.dataframe.shape[1])

        self._validate_on_empty(row_count=self.dataframe.shape[0], column_count=self.dataframe.shape[1])
        return self
