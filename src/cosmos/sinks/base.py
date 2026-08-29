from abc import ABC, abstractmethod
from typing import Literal

from pydantic import BaseModel, Field


class BaseSink(ABC, BaseModel):
    @abstractmethod
    def handle(self) -> None:
        """Abstract method to be implemented by all sinks for handling data."""
        pass

    def write_sink(self) -> None:
        """Abstract method to be implemented by all sinks for handling data."""
        pass


class BaseFileFormat(BaseSink):
    format: Literal["file"]
    path: str = Field(description="Path to store the report file.")

    def handle(self) -> None:
        raise NotImplementedError("Handle method must be implemented by the subclass.")


class BaseTableFormat(BaseSink):
    format: Literal["table"]

    def handle(self) -> None:
        raise NotImplementedError("Handle method must be implemented by the subclass.")
