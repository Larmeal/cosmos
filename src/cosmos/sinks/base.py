from abc import ABC, abstractmethod
from typing import Literal

from pydantic import BaseModel, Field

from cosmos.results import CosmosResult


class BaseSink(ABC, BaseModel):
    @abstractmethod
    def _handle(self) -> None:
        """Abstract method to be implemented by all sinks for handling data."""
        pass

    @abstractmethod
    def write_sink(self, result: CosmosResult) -> None:
        """Abstract method to be implemented by all sinks for handling data."""
        pass


class BaseFileFormat(BaseSink):
    format: Literal["file"]
    path: str = Field(description="Path to store the report file.")


class BaseTableFormat(BaseSink):
    format: Literal["table"]
