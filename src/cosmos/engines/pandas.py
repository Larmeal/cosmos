from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from cosmos.engines.base import BaseEngine

if TYPE_CHECKING:
    import pandas as pd


class PandasEngine(BaseEngine):
    """Engine class for handling data operations using pandas."""

    engine: Literal["pandas"]

    def statistics(self, data: pd.DataFrame) -> dict[str, Any]:
        return {
            "row_count": data.shape[0],
            "column_count": data.shape[1],
            "columns": data.columns.tolist(),
        }

    def load_data(self, file_path: str | Path) -> pd.DataFrame:
        import pandas as pd

        match self.source.file_format:
            case "csv":
                df = pd.read_csv(file_path, **self.source.options)
                return df
            case _:
                raise ValueError(f"Unsupported source type: {self.source.file_format}")
