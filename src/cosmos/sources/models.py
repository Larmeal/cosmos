from typing import Any, Literal

from pydantic import BaseModel, Field


class SourceConfig(BaseModel):
    """Configuration for the input data source.

    Attributes:
        type: The storage backend type. Restricted to specific literal values.
        file_format: The format of the file (e.g., 'csv', 'parquet').
        file_path: The URI or local path to the data.
        options: Additional reading options (e.g., delimiter, header rules).
    """

    type: Literal["local", "aws", "gcp", "azure"]
    file_format: str
    file_path: str
    options: dict[str, Any] = Field(default_factory=dict)
