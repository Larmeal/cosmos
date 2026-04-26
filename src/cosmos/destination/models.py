from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class OnFailureActionConfig(BaseModel):
    """What to do when GX validation fails.

    Actions and their required fields:

    - ``metadata_only``: Export validation metadata (errors, stats, run info) to a
        destination for later lookup. Requires ``type``, ``file_format``, ``file_path``.
    - ``move_file``: Move the raw source file to a failure zone. Requires ``type``,
        ``file_format``, ``file_path``.
    - ``copy_file``: Copy the raw source file to a failure zone. Requires ``type``,
        ``file_format``, ``file_path``.
    - ``delete_file``: Delete the raw source file in-place. No destination required.

    Attributes:
        type: Storage backend for the failure destination.
        action: The operation to perform on failure.
        file_format: Format of the file written to the failure destination.
        file_path: Path where the failure output (metadata or raw data) is written.
    """

    type: Literal["local", "aws", "gcp", "azure"] | None = None
    action: Literal["metadata_only", "move_file", "copy_file", "delete_file"]
    file_format: str | None = None
    file_path: str | None = None

    @model_validator(mode="after")
    def validate_relocation_fields(self) -> "OnFailureActionConfig":
        """Require destination fields for actions that write output on failure.

        ``metadata_only``, ``move_file``, and ``copy_file`` all write to a
        destination and therefore require ``type``, ``file_format``, and
        ``file_path``. ``delete_file`` removes the source in-place and needs
        no destination.
        """
        if self.action in {"move_file", "copy_file", "metadata_only"}:
            missing = [
                field
                for field in ("type", "file_format", "file_path")
                if getattr(self, field) is None
            ]
            if missing:
                raise ValueError(
                    f"on_failure_action with action='{self.action}' requires: {', '.join(missing)}"
                )
        return self


class DestinationConfig(BaseModel):
    """Configuration for the output sink of validated data.

    This is where the successfully processed data is written.
    The nested ``on_failure_action`` controls what happens to the
    *raw source file* when GX validation fails — it is separate from
    the destination itself.

    Attributes:
        type: Storage backend type for the output.
        file_format: Format of the output file (e.g., 'csv', 'parquet').
        file_path: URI or local path where the output should be saved.
        on_failure_action: Action to apply to the raw source data on failure.
        options: Additional writing options (e.g., compression, header rules).
    """

    type: Literal["local", "aws", "gcp", "azure"]
    file_format: str
    file_path: str
    on_failure_action: OnFailureActionConfig | None = None
    options: dict[str, Any] = Field(default_factory=dict)
