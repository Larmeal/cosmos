from abc import ABC, abstractmethod
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from cosmos.result import ActionName
from cosmos.storage import StorageBackend


class BaseFailureAction(BaseModel, ABC):
    """Base configuration for all failure actions.

    All actions need to know which storage they are operating on.
    """

    model_config = ConfigDict(extra="forbid")

    @abstractmethod
    def handle(self) -> None:
        """Perform the action on the source file."""

    def execute(self) -> None:
        return self.handle()


class IgnoreFailureAction(BaseFailureAction):
    """Leave the source file where it is.

    The default. Ignoring applies to the file alone: a report is still written,
    naming the file and what failed in it. No destination path is required.
    """

    action: Literal[ActionName.IGNORE] = Field(
        default=ActionName.IGNORE,
        description="Action identifier, fixed to 'ignore'. The file is left untouched; the report is still written.",
    )

    def handle(self) -> None:
        """Do nothing to the source file."""
        return None


class DeleteFailureAction(BaseFailureAction):
    """Configuration for deleting the raw source file in-place."""

    action: Literal[ActionName.DELETE] = Field(description="Action identifier, fixed to 'delete'.")
    storage: StorageBackend | None = Field(
        default=None,
        description="The storage backend to use for the action. If not provided, the storage backend will be inferred from the source configuration.",
    )

    def handle(self) -> None:
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
    storage: StorageBackend | None = Field(
        default=None,
        description="The storage backend to use for the action. If not provided, the storage backend will be inferred from the source configuration.",
    )

    @field_validator("dead_letter", mode="after")
    @classmethod
    def validate_local_dead_letter_path(cls, value: str) -> str:
        """Validator to ensure that dead_letter for local storage is not empty or root directory"""

        cleaned_path = value.rstrip("/")
        if not cleaned_path or cleaned_path == "/":
            raise ValueError("dead_letter cannot be empty or root directory ('/')")

        return cleaned_path

    def handle(self) -> None:
        """Handle the relocation action.

        This method is intended to be overridden by subclasses that implement specific relocation actions.
        """
        raise NotImplementedError("Subclasses must implement the handle method for relocation actions.")


class MoveFailureAction(RelocateFailureAction):
    """Configuration for moving the raw source file to a dead-letter directory."""

    action: Literal[ActionName.MOVE] = Field(description="Action identifier, fixed to 'move'.")

    def handle(self) -> None:
        """Handle the relocation action.

        This method is intended to be overridden by subclasses that implement specific relocation actions.
        """
        raise NotImplementedError("Subclasses must implement the handle method for relocation actions.")


class CopyFailureAction(RelocateFailureAction):
    """Configuration for copying the raw source file to a dead-letter directory."""

    action: Literal[ActionName.COPY] = Field(description="Action identifier, fixed to 'copy'.")

    def handle(self) -> None:
        """Handle the relocation action.

        This method is intended to be overridden by subclasses that implement specific relocation actions.
        """
        raise NotImplementedError("Subclasses must implement the handle method for relocation actions.")


OnFailureActionConfig = Annotated[
    IgnoreFailureAction | DeleteFailureAction | MoveFailureAction | CopyFailureAction,
    Field(discriminator="action"),
]
