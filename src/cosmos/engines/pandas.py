from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from cosmos.engines.base import BaseEngine

if TYPE_CHECKING:
    import pandas as pd

logger = logging.getLogger(__name__)


class PandasEngine(BaseEngine):
    """Engine class for handling data operations using pandas."""

    engine: Literal["pandas"]

    def is_empty(self, data: pd.DataFrame) -> bool:
        return data.empty

    def statistics(self, data: pd.DataFrame) -> dict[str, Any]:
        return {
            "row_count": data.shape[0],
            "column_count": data.shape[1],
            "columns": data.columns.tolist(),
        }

    def load_data(self, file_path: str | Path) -> pd.DataFrame:
        import pandas as pd

        logger.debug("loading %s as %s with options %s", file_path, self.source.file_format, self.source.options)

        match self.source.file_format:
            case "csv":
                df = pd.read_csv(file_path, **self.source.options)
            case _:
                raise ValueError(f"Unsupported source type: {self.source.file_format}")

        self._validate_on_empty(df)
        logger.info("loaded %s: %d row(s), %d column(s)", file_path, df.shape[0], df.shape[1])
        return df
