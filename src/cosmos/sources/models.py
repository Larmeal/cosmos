from textwrap import dedent
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class BaseConfig(BaseModel):
    """Base configuration class for all components.

    This class serves as a foundation for other configuration classes,
    providing common attributes and validation logic.

    Attributes:
        name: The name of the component.
        description: A brief description of the component's purpose.
    """

    model_config = ConfigDict(extra="forbid")


class FileBaseConfig(BaseConfig):
    """Base configuration class for all data sources.

    This class holds common attributes shared across different storage backends
    to enforce the DRY (Don't Repeat Yourself) principle.

    Attributes:
        file_format: The format of the file (e.g., 'csv', 'parquet', 'json').
        file_path: The path or URI to the data.
        options: Additional engine-specific reading options (e.g., delimiter, header).
    """

    file_format: str = Field(description="The format of the source file (e.g., 'csv', 'parquet', 'json').")
    file_path: str = Field(description="The path or URI pointing to the source data file including file name.")
    on_empty: Literal["fail", "skip"] = Field(
        default="skip",
        description="The action to take when the source file is empty. Options are 'fail' or 'skip'.",
    )
    options: dict[str, Any] = Field(
        default_factory=dict,
        description=dedent(
            """
        Additional engine-specific reading options (e.g., delimiter, header). You can specify any options that are supported by the underlying data reading engine.

        Example: For CSV files in pandas, you might specify
            {
                'delimiter': ',',
                'header': True
            }
        See https://pandas.pydata.org/docs/reference/io.html for the pandas reader options.
        """,
        ).strip(),
    )


class LocalSourceConfig(FileBaseConfig):
    """Configuration for a local file source.

    Attributes:
        storage: The storage backend type, fixed to 'local'.
        file_format: The format of the file (e.g., 'csv', 'parquet').
        file_path: The local path to the data.
        options: Additional reading options (e.g., delimiter, header rules).
    """

    storage: Literal["local"] = Field(description="Storage backend type, fixed to 'local'.")

    @field_validator("file_path")
    @classmethod
    def validate_file_path(cls, value: str) -> str:
        """Validate the local file path to ensure it exists and is a file.

        Args:
            value (str): The local file path to validate."""

        if "://" in value:
            raise ValueError(f"The provided file path '{value}' is not a valid local path.")
        return value


class GCPSourceConfig(FileBaseConfig):
    """Configuration for a Google Cloud Storage source.

    Attributes:
        storage: The storage backend type, fixed to 'gcp'.
        file_format: The format of the file (e.g., 'csv', 'parquet').
        file_path: The URI to the data in GCS (e.g., 'gs://bucket_name/path/to/file').
        options: Additional reading options (e.g., delimiter, header rules).
    """

    storage: Literal["gcp"] = Field(description="Storage backend type, fixed to 'gcp'.")

    @field_validator("file_path")
    @classmethod
    def validate_gcs_path(cls, value: str) -> str:
        """Validate the GCS file path to ensure it starts with 'gs://'.

        Args:
            value (str): The GCS file path to validate.

        Returns:
            str: The validated GCS file path.

        Raises:
            ValueError: If the GCS file path does not start with 'gs://'.
        """
        if not value.startswith("gs://"):
            raise ValueError(f"The provided file path '{value}' is not a valid GCS path. It must start with 'gs://'.")
        return value


SourceConfig = Annotated[LocalSourceConfig | GCPSourceConfig, Field(discriminator="storage")]
