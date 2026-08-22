from __future__ import annotations

from abc import ABC
from textwrap import dedent
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class BaseConfig(BaseModel, ABC):
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
