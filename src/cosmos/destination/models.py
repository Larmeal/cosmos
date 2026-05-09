from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, field_validator


class BaseFailureAction(BaseModel):
    """Base configuration for all failure actions.

    All actions need to know which storage backend they are operating on.
    """

    type: Literal["local", "aws", "gcp", "azure"] = Field(
        description="The storage backend type this action operates on."
    )


class IgnoreFailureAction(BaseFailureAction):
    """Configuration for ignoring the failure.

    The framework will do nothing to the raw source file and will simply
    let the pipeline fail. No storage type or destination paths are required.
    """

    action: Literal["ignore"] = Field(
        description="Action identifier, fixed to 'ignore'."
    )


class DeleteFailureAction(BaseFailureAction):
    """Configuration for deleting the raw source file in-place."""

    action: Literal["delete_file"] = Field(
        description="Action identifier, fixed to 'delete_file'."
    )


class RelocateFailureAction(BaseFailureAction):
    """Configuration for actions that require a destination path."""

    action: Literal["metadata_only", "move_file", "copy_file"] = Field(
        description="The relocation action to perform: save metadata only, move, or copy the file."
    )
    dir_path: str = Field(
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

    @field_validator("dir_path", mode="after")
    @classmethod
    def validate_local_dir_path(cls, value: str) -> str:
        """Validator to ensure that dir_path for local storage is not empty or root directory"""

        cleaned_path = value.rstrip("/")
        if not cleaned_path or cleaned_path == "/":
            raise ValueError("dir_path cannot be empty or root directory ('/')")

        return cleaned_path


OnFailureActionConfig = Annotated[
    IgnoreFailureAction | DeleteFailureAction | RelocateFailureAction,
    Field(discriminator="action"),
]


class BaseDestinationConfig(BaseModel):
    """Configuration for the output sink of validated data.

    This is where the successfully processed data is written.
    The nested ``on_failure_action`` controls what happens to the
    *raw source file* when GX validation fails — it is separate from
    the destination itself.

    Attributes:
        type: Storage backend type for the output.
        dir_path: URI or local path where the output should be saved.
        on_failure_action: Action to apply to the raw source data on failure.
        options: Additional writing options (e.g., compression, header rules).
    """

    dir_path: str = Field(
        description="Local path or cloud URI of the directory where the output should be written."
    )
    on_failure_action: OnFailureActionConfig | None = Field(
        default=None,
        description="Action to apply to the raw source data when GX validation fails.",
    )
    options: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional backend-specific writing options (e.g., compression, header rules).",
    )


class LocalDestinationConfig(BaseDestinationConfig):
    """Configuration for a local file destination.

    Attributes:
        type: Storage backend type, fixed to 'local'.
        dir_path: Local path where the output should be saved.
        on_failure_action: Action to apply to the raw source data on failure.
        options: Additional writing options (e.g., compression, header rules).
    """

    type: Literal["local"] = Field(
        default="local", description="Storage backend type, fixed to 'local'."
    )


class GCPDestinationConfig(BaseDestinationConfig):
    """Configuration for a Google Cloud Storage destination.

    Attributes:
        type: Storage backend type, fixed to 'gcp'.
        dir_path: URI to the output location in GCS (e.g., 'gs://bucket_name/path/to/directory').
        on_failure_action: Action to apply to the raw source data on failure.
        options: Additional writing options (e.g., compression, header rules).
    """

    type: Literal["gcp"] = Field(
        default="gcp", description="Storage backend type, fixed to 'gcp'."
    )


DestinationConfig = Annotated[
    LocalDestinationConfig | GCPDestinationConfig, Field(discriminator="type")
]
