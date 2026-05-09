from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, model_validator


class BaseSourceConfig(BaseModel):
    """Base configuration class for all data sources.

    This class holds common attributes shared across different storage backends
    to enforce the DRY (Don't Repeat Yourself) principle.

    Attributes:
        file_format: The format of the file (e.g., 'csv', 'parquet', 'json').
        file_path: The path or URI to the data.
        options: Additional engine-specific reading options (e.g., delimiter, header).
    """

    file_format: str = Field(
        description="The format of the source file (e.g., 'csv', 'parquet', 'json')."
    )
    file_path: str = Field(
        description="The path or URI pointing to the source data file."
    )
    options: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional engine-specific reading options (e.g., delimiter, header).",
    )

    @model_validator(mode="after")
    def validate_local_file_path(self) -> "BaseSourceConfig":
        """Validator to ensure that file_path extension matches file_format"""

        if Path(self.file_path).suffix.lower() != f".{self.file_format.lower()}":
            raise ValueError(
                f"`file_path` must end with a file extension matching `file_format` (.{self.file_format.lower()}). Got: {self.file_path}"
            )

        return self


class LocalSourceConfig(BaseSourceConfig):
    """Configuration for a local file source.

    Attributes:
        type: The storage backend type, fixed to 'local'.
        file_format: The format of the file (e.g., 'csv', 'parquet').
        file_path: The local path to the data.
        options: Additional reading options (e.g., delimiter, header rules).
    """

    type: Literal["local"] = Field(
        description="Storage backend type, fixed to 'local'."
    )


class GCPSourceConfig(BaseSourceConfig):
    """Configuration for a Google Cloud Storage source.

    Attributes:
        type: The storage backend type, fixed to 'gcp'.
        file_format: The format of the file (e.g., 'csv', 'parquet').
        file_path: The URI to the data in GCS (e.g., 'gs://bucket_name/path/to/file').
        options: Additional reading options (e.g., delimiter, header rules).
    """

    type: Literal["gcp"] = Field(description="Storage backend type, fixed to 'gcp'.")


SourceConfig = Annotated[
    LocalSourceConfig | GCPSourceConfig, Field(discriminator="type")
]

# Backwards-compatible alias
SourceConfigType = SourceConfig
