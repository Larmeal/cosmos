import datetime
from enum import StrEnum
from importlib.metadata import version
from typing import Any

from pydantic import BaseModel, Field

_COSMOS_VERSION = version("cosmos")


class ActionName(StrEnum):
    """What COSMOS can do to a source file once ``on_failure`` decides to act.

    Mirrors the ``action`` field of the ``on_failure`` config block one-to-one.
    The YAML author picks one of these four, and ``policy.py`` copies that
    same value onto the ``ActionResult`` it plans, unchanged.

    Values:
        IGNORE: Leave the file exactly where it is. Also the value
            ``policy.py`` uses when nothing needs to happen at all, not only
            when the user configured it explicitly.
        DELETE: Remove the file from its source location.
        MOVE: Relocate the file into ``dead_letter``, removing the original.
        COPY: Copy the file into ``dead_letter``, leaving the original in place.

    Example:
        >>> ActionName.MOVE
        <ActionName.MOVE: 'move'>

        >>> ActionName.MOVE.value
        'move'

        >>> ActionName.MOVE == "move"
        True
    """

    IGNORE = "ignore"
    DELETE = "delete"
    MOVE = "move"
    COPY = "copy"


class ActionStatus(StrEnum):
    """Where one ``ActionResult`` is in its own lifecycle, separate from which action it names.

    ``policy.py`` only ever produces ``PENDING`` or ``SKIPPED``. The runner
    is what moves a ``PENDING`` row to ``COMPLETED`` or ``FAILED`` once it
    has actually tried to perform the action.

    A row still at ``PENDING`` in a written report means the process died
    between planning the action and carrying it out.

    Values:
        PENDING: The action is due but has not run yet.
        SKIPPED: Nothing needs to touch the file, e.g. the decision was
            ``PASSED`` or ``WARNED``.
        COMPLETED: The runner performed the action and it succeeded.
        FAILED: The runner tried to perform the action and it raised.

    Example:
        >>> ActionStatus.PENDING
        <ActionStatus.PENDING: 'pending'>

        >>> ActionStatus.PENDING == "pending"
        True
    """

    PENDING = "pending"
    SKIPPED = "skipped"
    COMPLETED = "completed"
    FAILED = "failed"


class Decision(StrEnum):
    """Was the data itself good, for one source object or for the whole run.

    Derived from expectation severities, not from whether COSMOS managed to
    run at all. An object that could not be read has no ``Decision``, because
    there was no data to judge (see ``RunObjectStatus.ABORTED``).

    Values:
        PASSED: No expectation failed, or only ``info`` ones did.
        WARNED: The worst failing expectation was ``warning``.
        FAILED: At least one ``critical`` expectation failed.

    Only ``FAILED`` ever triggers the configured ``on_failure`` action. The
    other two leave the file untouched but are still written to the report.

    At the run level, ``CosmosResult.decision`` rolls these up across every
    object. This is the "is the data okay" verdict, read by whoever owns the
    data, as opposed to ``RunStatus``, which answers "did COSMOS do its job"
    and is read by whoever runs the pipeline.

    Example:
        >>> Decision.FAILED
        <Decision.FAILED: 'failed'>

        >>> Decision.FAILED == "failed"
        True
    """

    PASSED = "passed"
    WARNED = "warned"
    FAILED = "failed"


class RunStatus(StrEnum):
    """Did COSMOS manage to do its job for this run, independent of what the data looked like.

    A rollup of every object's ``RunObjectStatus``, not of their
    ``Decision``. A run where every single file failed every expectation is
    still ``COMPLETED``, because COSMOS read and validated all of them
    successfully.

    Values:
        COMPLETED: Every object completed, including an empty, allowed glob.
        PARTIAL: A mix of completed and aborted objects.
        ABORTED: Every object aborted.

    ``ABORTED`` is deliberately louder than ``PARTIAL``: every object
    failing to even run points at something systemic (bad credentials, a
    network outage), not at ordinary bad data, and should draw attention
    first.

    ``PARTIAL`` is the everyday case of "partial failure continues": most
    files were fine, a few individually could not be read, and the rest
    still ran.

    Read by whoever runs the pipeline; ``Decision`` is read by whoever owns
    the data.

    Example:
        >>> RunStatus.PARTIAL
        <RunStatus.PARTIAL: 'partial'>

        >>> RunStatus.PARTIAL == "partial"
        True
    """

    COMPLETED = "completed"
    PARTIAL = "partial"
    ABORTED = "aborted"


class RunObjectStatus(StrEnum):
    """Did COSMOS finish processing one source object, independent of the verdict.

    Set once per object, before ``Decision`` is even known.

    Values:
        COMPLETED: The object was read and every expectation ran, whatever
            the result was.
        ABORTED: Something raised before that point instead, e.g. a corrupt
            file or an unreadable encoding, caught by the runner's
            ``try/except`` around the read and validate steps.

    ``RunStatus`` is the rollup of these two values across every object in
    the run.

    Example:
        >>> RunObjectStatus.ABORTED
        <RunObjectStatus.ABORTED: 'aborted'>

        >>> RunObjectStatus.ABORTED == "aborted"
        True
    """

    COMPLETED = "completed"
    ABORTED = "aborted"


class Severity(StrEnum):
    """COSMOS's own mirror of GX's ``FailureSeverity``: same three levels, no GX import.

    Building a GX expectation suite requires a ``FailureSeverity`` value
    (from ``great_expectations.expectations.metadata_types``), but
    ``results.py`` is a leaf module that must import nothing of ours and
    nothing of GX's, so every other module can depend on it without dragging
    ``great_expectations`` in transitively.

    Declaring an equivalent enum here instead keeps that boundary intact;
    ``gx/validator.py``'s ``_map_severity`` is the only place that translates
    between the two.

    Values:
        CRITICAL: A failure triggers the configured ``on_failure`` action.
        WARNING: A failure is recorded but the file is left alone.
        INFO: A failure is recorded as a note for a person, nothing more.

    Example:
        >>> Severity.CRITICAL
        <Severity.CRITICAL: 'critical'>

        >>> Severity.CRITICAL == "critical"
        True
    """

    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class SourceObjectMetadata(BaseModel):
    """Resolved reality for one source object: where it is, how big, how old.

    Produced by ``storage.glob``: every backend fills the same three required
    fields from its own listing, so a missing one fails at construction rather
    than surfacing as a hole in the report. ``metadata`` is a backend-specific
    bag that nothing downstream interprets.
    """

    path: str = Field(description="Full URI of the source object, the report's source_object key.")
    size_bytes: int = Field(description="Object size in bytes, from the listing.")
    modified: datetime.datetime = Field(description="Last-modified time (UTC), from the listing.")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Backend-specific extras nothing downstream interprets (e.g. GCS etag, md5_hash).",
    )


class ExpectationResult(BaseModel):
    """The outcome of one expectation against one source object: one row in the report.

    Filled by ``gx/`` and never touched again. The fields promoted out of GX's
    nested dicts are exactly the ones something outside ``gx/`` reads: ``severity``
    and ``success`` drive the policy decision, the rest become report columns.
    ``exception_message`` is separate from ``success`` on purpose: a rule GX could
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
    severity: Severity | str = Field(
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
    raised_exception: bool = Field(
        default=False,
        description="Indicates whether an exception was raised during the expectation check.",
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
    status: ActionStatus = Field(description="Indicates the status of the action.")
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

    Accretes across the run rather than being built at once: the planner supplies
    ``source_object``, the reader the counts and timings, ``gx/`` the expectations,
    the policy the decision, the action its outcome. Most fields are therefore
    optional because they are genuinely unknown at construction, not from laxity:
    an object that could not be read has no ``row_count`` and no expectations, yet
    still has to be recorded and dead-lettered.
    """

    status: RunObjectStatus = Field(description="The status of the validation operation.")
    source_object: SourceObjectMetadata = Field(
        description="The identifier or name of the source object being validated."
    )
    row_count: int | None = Field(description="The number of rows processed during the validation operation.")
    column_count: int | None = Field(description="The number of columns processed during the validation operation.")
    read_duration_sec: float | None = Field(default=None, description="The duration of the read operation in seconds.")
    validation_duration_sec: float | None = Field(description="The duration of the validation operation in seconds.")
    error_type: str | None = Field(
        description="The type of error that occurred during the validation operation, if any.",
    )
    error_message: str | None = Field(
        description="The error message associated with the error that occurred during the validation operation, if any.",
    )
    decision: Decision | None = Field(
        description="The decision made based on the validation results, if any.",
    )
    expectations: list[ExpectationResult] | None = Field(
        description="The list of expectation results for the source object.",
    )
    action: ActionResult | None = Field(
        description="The result of the action taken after the validation operation, if any.",
    )
    raw_gx_result: dict | None = Field(
        description="The raw result from the GX operation, if any.",
        exclude=True,
    )


class CosmosResult(BaseModel):
    """The result of one run: what the library returns and what the sinks write.

    The reasoning a CLI exit code cannot carry: which objects were checked, what was
    decided about each, and what was done to them. Run-level verdicts are summaries
    of ``results`` and nothing else decides them.
    """

    cosmos_version: str = Field(
        default=_COSMOS_VERSION,
        description="The version of Cosmos used for the validation.",
    )
    run_id: str = Field(description="The unique identifier for the specific run of the Cosmos operation.")
    run_ts: datetime.datetime = Field(description="The timestamp of the specific run of the Cosmos operation.")
    results: list[SourceObjectResult] = Field(
        description=(
            "One entry per source object the planner resolved. Every planned object ends up here "
            "whether it validated or aborted, so an empty list means the glob matched nothing."
        )
    )
    run_status: RunStatus = Field(
        description=(
            "Did COSMOS manage to do its job: a rollup of results[].status, which is only "
            "'completed' or 'aborted' per object. Empty results: 'completed', because the glob "
            "matched nothing and source.on_empty allowed it. All completed: 'completed'. "
            "All aborted: 'aborted', which is systemic and should be louder than 'partial'. "
            "Otherwise 'partial'. Answers a different question from data_decision: this one is "
            "read by whoever runs the pipeline, that one by whoever owns the data."
        )
    )
    decision: Decision | None = Field(
        description="The overall data decision based on the validation results, if any.",
    )
