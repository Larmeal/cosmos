from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from cosmos.actions import DeleteFailureAction, IgnoreFailureAction, OnFailureActionConfig, RelocateFailureAction
from cosmos.exceptions.data_error import SourceEmptyError
from cosmos.gx.models import GXConfig
from cosmos.sinks import SinkConfig
from cosmos.sources import SourceConfig

if TYPE_CHECKING:
    pass


class BaseEngine(BaseModel, ABC):
    """Base class for all engine implementations.

    This class serves as a foundation for specific engine implementations,
    providing common attributes and methods that can be shared across different engines.

    Attributes:
        engine: The type of engine (e.g., 'pandas', 'spark', 'sql').
    """

    # arbitrary_types_allowed: `dataframe` holds a pd.DataFrame / SparkDataFrame,
    # neither of which pydantic knows how to build a schema for on its own.
    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

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
    dataframe: Any | None = Field(
        default=None,
        description="Holds the loaded data after calling the load_data method.",
    )

    @model_validator(mode="after")
    def _inherit_storage_for_action(self) -> Self:
        if (
            isinstance(self.on_failure, DeleteFailureAction) or isinstance(self.on_failure, RelocateFailureAction)
        ) and self.on_failure.backend is None:
            self.on_failure.backend = self.source.backend
        return self

    @abstractmethod
    def is_empty(self) -> bool:
        """Check if ``self.dataframe`` is empty. Only meaningful after ``load_data`` has run."""

    def _validate_on_empty(self, row_count: int | None = None, column_count: int | None = None) -> None:
        """Raise ``SourceEmptyError`` when ``self.dataframe`` has no rows to validate.

        Always raises on empty data; it does not decide what that means. Whether an
        empty object is skipped or treated as a failure is a run-level policy
        decision (``source.on_empty``), made once by the runner for every empty
        object the same way, whether the emptiness was detected here (a header with
        no rows) or further back, while reading (zero bytes, no header at all).
        ``row_count``/``column_count`` are passed through to the exception so the
        report can still state the shape even though it interrupts ``load_data``
        before it returns.
        """
        if self.is_empty():
            raise SourceEmptyError(f"{self.source.file_path} is empty", row_count=row_count, column_count=column_count)

    @abstractmethod
    def statistics(self) -> dict[str, Any]:
        """Return engine-specific statistics about ``self.dataframe``."""

    @abstractmethod
    def load_data(self, file_path: str) -> Self:
        """Load data from the specified source into ``self.dataframe``.

        This method should be implemented by subclasses to handle the specific
        logic for loading data based on the engine type.

        Returns:
            ``self``, so the caller can chain ``is_empty()`` / ``statistics()``
            against the data this call just loaded, builder-style.
        """
