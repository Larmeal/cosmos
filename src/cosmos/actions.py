from abc import ABC, abstractmethod
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from cosmos.storage.base import BaseStorage


class BaseFailureAction(BaseModel, ABC):
    """Base configuration for all failure actions.

    All actions need to know which storage they are operating on.
    """

    model_config = ConfigDict(extra="forbid")

    @abstractmethod
    def handle(self, storage: BaseStorage) -> None:
        """Perform the action on the source file."""

    def execute(self, storage: BaseStorage) -> None:
        return self.handle(storage=storage)


class IgnoreFailureAction(BaseFailureAction):
    """Leave the source file where it is.

    The default. Ignoring applies to the file alone: a report is still written,
    naming the file and what failed in it. No destination path is required.
    """

    action: Literal["ignore"] = Field(
        default="ignore",
        description="Action identifier, fixed to 'ignore'. The file is left untouched; the report is still written.",
    )

    def handle(self, storage: BaseStorage) -> None:
        """Do nothing to the source file."""
        return None


class DeleteFailureAction(BaseFailureAction):
    """Configuration for deleting the raw source file in-place."""

    action: Literal["delete"] = Field(description="Action identifier, fixed to 'delete'.")

    def handle(self, storage: BaseStorage) -> None:
        """Handle the delete action.

        This method deletes the raw source file in-place using the provided storage backend.
        """
        raise NotImplementedError("Subclasses must implement the handle method for relocation actions.")


class RelocateFailureAction(BaseFailureAction):
    """Configuration for actions that require a destination path."""

    dead_letter: str = Field(
        description=(
            "The directory path where the file should be moved/copied or where metadata should be saved. "
            "Supports both relative and absolute paths for local storage, "
            "and should be a valid URI for cloud storage (e.g., 'gs://bucket_name/path/to/directory')."
        ),
        examples=[
            "./data/dead-letters",
            "./data/dead-letters/",
            "gs://my-bucket/dead-letters",
            "gs://my-bucket/dead-letters/",
        ],
    )

    @field_validator("dead_letter", mode="after")
    @classmethod
    def validate_local_dead_letter_path(cls, value: str) -> str:
        """Validator to ensure that dead_letter for local storage is not empty or root directory"""

        cleaned_path = value.rstrip("/")
        if not cleaned_path or cleaned_path == "/":
            raise ValueError("dead_letter cannot be empty or root directory ('/')")

        return cleaned_path

    def handle(self, storage: BaseStorage) -> None:
        """Handle the relocation action.

        This method is intended to be overridden by subclasses that implement specific relocation actions.
        """
        raise NotImplementedError("Subclasses must implement the handle method for relocation actions.")


class MoveFailureAction(RelocateFailureAction):
    """Configuration for moving the raw source file to a dead-letter directory."""

    action: Literal["move"] = Field(description="Action identifier, fixed to 'move'.")

    def handle(self, storage: BaseStorage) -> None:
        """Handle the relocation action.

        This method is intended to be overridden by subclasses that implement specific relocation actions.
        """
        raise NotImplementedError("Subclasses must implement the handle method for relocation actions.")


class CopyFailureAction(RelocateFailureAction):
    """Configuration for copying the raw source file to a dead-letter directory."""

    action: Literal["copy"] = Field(description="Action identifier, fixed to 'copy'.")

    def handle(self, storage: BaseStorage) -> None:
        """Handle the relocation action.

        This method is intended to be overridden by subclasses that implement specific relocation actions.
        """
        raise NotImplementedError("Subclasses must implement the handle method for relocation actions.")


OnFailureActionConfig = Annotated[
    IgnoreFailureAction | DeleteFailureAction | MoveFailureAction | CopyFailureAction,
    Field(discriminator="action"),
]
