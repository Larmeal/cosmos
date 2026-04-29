from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field


class BaseSourceConfig(BaseModel):
    """Base configuration class for all data sources.

    This class holds common attributes shared across different storage backends
    to enforce the DRY (Don't Repeat Yourself) principle.

    Attributes:
        file_format: The format of the file (e.g., 'csv', 'parquet', 'json').
        file_path: The path or URI to the data.
        options: Additional engine-specific reading options (e.g., delimiter, header).
    """

    file_format: str
    file_path: str
    options: dict[str, Any] = Field(default_factory=dict)


class LocalSourceConfig(BaseSourceConfig):
    """Configuration for a local file source.

    Attributes:
        type: The storage backend type, fixed to 'local'.
        file_format: The format of the file (e.g., 'csv', 'parquet').
        file_path: The local path to the data.
        options: Additional reading options (e.g., delimiter, header rules).
    """

    type: Literal["local"]


class GCPSourceConfig(BaseSourceConfig):
    """Configuration for a Google Cloud Storage source.

    Attributes:
        type: The storage backend type, fixed to 'gcp'.
        file_format: The format of the file (e.g., 'csv', 'parquet').
        file_path: The URI to the data in GCS (e.g., 'gs://bucket_name/path/to/file').
        options: Additional reading options (e.g., delimiter, header rules).
    """

    type: Literal["gcp"]


SourceConfigType = Annotated[
    LocalSourceConfig | GCPSourceConfig, Field(discriminator="type")
]
