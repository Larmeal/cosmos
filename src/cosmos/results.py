import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field


class ActionName(StrEnum):
    IGNORE = "ignore"
    DELETE = "delete"
    MOVE = "move"
    COPY = "copy"


class Severity(StrEnum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class SourceObjectMetadata(BaseModel):
    """Resolved reality for one source object: where it is, how big, how old.

    Produced by ``storage.glob`` — every backend fills the same three required
    fields from its own listing, so a missing one fails at construction rather
    than surfacing as a hole in the report. ``metadata`` is a backend-specific
    bag that nothing downstream interprets.
    """

    path: str = Field(description="Full URI of the source object — the report's source_object key.")
    size_bytes: int = Field(description="Object size in bytes, from the listing.")
    modified: datetime.datetime = Field(description="Last-modified time (UTC), from the listing.")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Backend-specific extras nothing downstream interprets (e.g. GCS etag, md5_hash).",
    )


class ExpectationResult(BaseModel):
    """The outcome of one expectation against one source object — one row in the report.

    Filled by ``gx/`` and never touched again. The fields promoted out of GX's
    nested dicts are exactly the ones something outside ``gx/`` reads: ``severity``
    and ``success`` drive the policy decision, the rest become report columns.
    ``exception_message`` is separate from ``success`` on purpose — a rule GX could
    not run is not a rule that passed.
    """

    success: bool = Field(description="Indicates whether the expectation was met.")
    expectation_name: str | None = Field(default=None, description="The name of the expectation that was checked.")
    expectation_type: str = Field(description="The type of the expectation that was checked.")
    expectation_key: str = Field(description="The unique key identifying the expectation that was checked.")
    expectation_kwargs: dict[str, Any] = Field(
        default_factory=dict,
        description="The keyword arguments passed to the expectation (e.g., {'column': 'id'}).",
    )
    description: str | None = Field(
        default=None,
        description="A human-readable description of the expectation.",
    )
    severity: Severity = Field(
        default=Severity.CRITICAL,
        description=(
            "The severity level if this expectation fails. 'critical' triggers the failure action, 'warning' and 'info' are recorded only."
        ),
    )
    element_count: int | None = Field(
        default=None,
        description="The number of elements checked by the expectation, if applicable.",
    )
    observed_value: Any | None = Field(
        default=None,
        description="The value observed during the expectation check, if applicable.",
    )
    unexpected_count: int | None = Field(
        default=None,
        description="The number of unexpected elements found by the expectation, if applicable.",
    )
    unexpected_percent: float | None = Field(
        default=None,
        description="The percentage of unexpected elements found by the expectation, if applicable.",
    )
    unexpected_values: list[Any] | None = Field(
        default=None,
        description="The list of unexpected values found by the expectation, if applicable.",
    )
    unexpected_index: list[int] | None = Field(
        default=None,
        description="The list of indices of unexpected elements found by the expectation, if applicable.",
    )
    exception_message: str | None = Field(
        default=None,
        description="The exception raised during the expectation check, if applicable.",
    )
    meta: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata about the expectation result, if applicable.",
    )
    notes: str | None = Field(
        default=None,
        description="Additional notes about the expectation result, if applicable.",
    )


class ActionResult(BaseModel):
    """What was done to the source object, and whether it worked.

    Written twice: ``status`` is ``pending`` when the report records the intent,
    then the same instance is updated once the action has run and the report is
    merged onto the same row. A row left at ``pending`` means the process died
    between the two, so this model is deliberately mutable.
    """

    action: ActionName = Field(description="The name of the action that was taken.")
    status: Literal["succeeded", "failed", "skipped"] = Field(
        description="Indicates whether the action was successful."
    )
    dead_letter: str | None = Field(
        default=None,
        description="The directory path where the file should be moved/copied or where metadata should be saved.",
    )
    error: str | None = Field(
        default=None,
        description="Error message if the action failed.",
    )


class SourceObjectResult(BaseModel):
    """Everything that happened to one source object.

    Accretes across the run rather than being built at once — the planner supplies
    ``source_object``, the reader the counts and timings, ``gx/`` the expectations,
    the policy the decision, the action its outcome. Most fields are therefore
    optional because they are genuinely unknown at construction, not from laxity:
    an object that could not be read has no ``row_count`` and no expectations, yet
    still has to be recorded and dead-lettered.
    """

    status: Literal["completed", "aborted"] = Field(description="The status of the validation operation.")
    source_object: SourceObjectMetadata = Field(
        description="The identifier or name of the source object being validated."
    )
    row_count: int | None = Field(
        default=None, description="The number of rows processed during the validation operation."
    )
    column_count: int | None = Field(
        default=None, description="The number of columns processed during the validation operation."
    )
    read_duration_sec: float | None = Field(default=None, description="The duration of the read operation in seconds.")
    validation_duration_sec: float | None = Field(
        default=None, description="The duration of the validation operation in seconds."
    )
    error_type: str | None = Field(
        default=None,
        description="The type of error that occurred during the validation operation, if any.",
    )
    error_message: str | None = Field(
        default=None,
        description="The error message associated with the error that occurred during the validation operation, if any.",
    )
    decision: Literal["pass", "warn", "fail"] | None = Field(
        default=None,
        description="The decision made based on the validation results, if any.",
    )
    expectations: list[ExpectationResult] = Field(
        default_factory=list,
        description="The list of expectation results for the source object.",
    )
    action: ActionResult | None = Field(
        default=None,
        description="The result of the action taken after the validation operation, if any.",
    )
    raw_gx_result: dict | None = Field(
        default=None,
        description="The raw result from the GX operation, if any.",
        exclude=True,
    )


class CosmosResult(BaseModel):
    """The result of one run — what the library returns and what the sinks write.

    The reasoning a CLI exit code cannot carry: which objects were checked, what was
    decided about each, and what was done to them. Run-level verdicts are summaries
    of ``results`` and nothing else decides them.
    """

    validation_id: str = Field(description="The unique identifier for the validation operation.")
    cosmos_version: str = Field(description="The version of Cosmos used for the validation.")
    attempt: int = Field(description="The attempt number for the specific run of the Cosmos operation.")
    run_id: str = Field(description="The unique identifier for the specific run of the Cosmos operation.")
    run_ts: datetime.datetime = Field(description="The timestamp of the specific run of the Cosmos operation.")
    results: list[SourceObjectResult] = Field(
        description=(
            "One entry per source object the planner resolved. Every planned object ends up here "
            "whether it validated or aborted, so an empty list means the glob matched nothing."
        )
    )

    run_status: Literal["completed", "partial", "aborted"] = Field(
        description=(
            "Did COSMOS manage to do its job — a rollup of results[].status, which is only "
            "'completed' or 'aborted' per object. Empty results: 'completed', because the glob "
            "matched nothing and source.on_empty allowed it. All completed: 'completed'. "
            "All aborted: 'aborted', which is systemic and should be louder than 'partial'. "
            "Otherwise 'partial'. Answers a different question from data_decision: this one is "
            "read by whoever runs the pipeline, that one by whoever owns the data."
        )
    )
    data_decision: Literal["pass", "warn", "fail"] | None = Field(
        default=None,
        description="The overall data decision based on the validation results, if any.",
    )
