from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from cosmos.actions import DeleteFailureAction, IgnoreFailureAction, OnFailureActionConfig, RelocateFailureAction
from cosmos.gx.models import GXConfig
from cosmos.sinks import SinkConfig
from cosmos.sources import SourceConfig

if TYPE_CHECKING:
    import pandas as pd
    from pyspark.sql import DataFrame as SparkDataFrame


class BaseEngine(BaseModel, ABC):
    """Base class for all engine implementations.

    This class serves as a foundation for specific engine implementations,
    providing common attributes and methods that can be shared across different engines.

    Attributes:
        engine: The type of engine (e.g., 'pandas', 'spark', 'sql').
    """

    model_config = ConfigDict(extra="forbid")

    id: str = Field(description="A unique identifier for the engine instance.")
    source: SourceConfig = Field(description="Configuration for the input data source.")
    validation: GXConfig = Field(
        description="Configuration for the Great Expectations validation workflow.",
    )
    report: SinkConfig = Field(
        description="Configuration for the output sink.",
    )
    on_failure: OnFailureActionConfig = Field(
        default_factory=IgnoreFailureAction,
        description="What to do with the source file when validation fails. Defaults to leaving it in place.",
    )

    @model_validator(mode="after")
    def _inherit_storage_for_action(self) -> Self:
        if (
            isinstance(self.on_failure, DeleteFailureAction) or isinstance(self.on_failure, RelocateFailureAction)
        ) and self.on_failure.backend is None:
            self.on_failure.backend = self.source.backend
        return self

    @abstractmethod
    def load_data(self, file_path: str, **options: Any) -> pd.DataFrame | SparkDataFrame | None:
        """Load data from the specified source.

        This method should be implemented by subclasses to handle the specific
        logic for loading data based on the engine type.

        Returns:
            The loaded data in a format appropriate for the engine (e.g., DataFrame).
        """
        pass
