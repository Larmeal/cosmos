from __future__ import annotations

import datetime
import logging
from collections.abc import Callable, Generator
from contextlib import contextmanager
from time import perf_counter
from typing import TYPE_CHECKING

from cosmos.engines import Engine
from cosmos.exceptions.data_error import SourceEmptyError
from cosmos.gx.translation import GXTranslateExpectationResult
from cosmos.gx.validator import GXValidator
from cosmos.policy import CosmosPolicy, SourceObjectPolicy
from cosmos.results import (
    ActionName,
    ActionResult,
    ActionStatus,
    CosmosResult,
    Decision,
    RunObjectStatus,
    RunStatus,
    SourceObjectMetadata,
    SourceObjectResult,
)

if TYPE_CHECKING:
    from cosmos.actions import OnFailureActionConfig
    from cosmos.gx.models import GXConfig
    from cosmos.sinks import SinkConfig
    from cosmos.sources import SourceConfig
    from cosmos.storages import StorageBackend

logger = logging.getLogger(__name__)


class Runner:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine
        self._storage = self.storage
        self._source = self.source
        self._validation = self.validation
        self._sink = self.sink
        self._on_failure = self.on_failure

    @property
    def on_failure(self) -> OnFailureActionConfig:
        return self.engine.on_failure

    @property
    def sink(self) -> SinkConfig:
        return self.engine.report

    @property
    def validation(self) -> GXConfig:
        return self.engine.validation

    @property
    def source(self) -> SourceConfig:
        return self.engine.source

    @property
    def storage(self) -> StorageBackend:
        return self.engine.source.backend

    def __repr__(self) -> str:
        return (
            f"Runner(id={self.engine.id!r}, "
            f"engine={self.engine.engine!r}, "
            f"source={self.source.file_path!r}, "
            f"contract={self.validation.contract.data_asset_name!r})"
        )

    @contextmanager
    def _timer(self) -> Generator[Callable[[], float]]:
        start = perf_counter()
        yield lambda: perf_counter() - start

    def _apply_action(self, action_result: ActionResult, src: str) -> Exception | None:
        """Performs the planned action and records whether it actually worked.

        Runs once the decision is already final, so a failure here never touches the
        decision, expectations or statistics already computed for this source object;
        it is returned instead, so the caller can still record the object as aborted
        without losing the verdict already reached. It also never raises on its own:
        any exception from the storage backend is caught and recorded on
        ``action_result``, so one file's action failing cannot abort the objects still
        left in the loop.
        """
        if action_result.action == ActionName.IGNORE:
            return None

        try:
            self.on_failure.handle(src=src)
            action_result.status = ActionStatus.COMPLETED
            return None
        except Exception as e:
            logger.exception("failed to apply action %s for %s", action_result.action, src)
            action_result.status = ActionStatus.FAILED
            action_result.error = str(e)
            return e

    def run(self) -> None:
        source_object_metadata: list[SourceObjectMetadata] = self.storage.glob(self.engine.source.file_path)
        logger.info("resolved %d source object(s) for %s", len(source_object_metadata), self.engine.source.file_path)

        source_object_results: list[SourceObjectResult] = []
        for source in source_object_metadata:
            source: SourceObjectMetadata

            try:
                with self._timer() as duration:
                    engine = self.engine.model_copy().load_data(file_path=source.path)

                read_duration_sec = duration()
                statistics = engine.statistics()

                with self._timer() as validation_duration:
                    gx_result = GXValidator(config=self.validation).validate(df=engine.dataframe)

                validation_duration_sec = validation_duration()

                cosmos_expectation_result = GXTranslateExpectationResult(
                    validation_config=self.validation.contract.expectations,
                ).translate(gx_result=gx_result)

                decision, action_result = SourceObjectPolicy(on_failure_config=self.on_failure).decide(
                    expectation_results=cosmos_expectation_result
                )
                error_type = None
                error_message = None
            except SourceEmptyError as e:
                read_duration_sec = None
                validation_duration_sec = None
                gx_result = None
                statistics = {"row_count": e.row_count, "column_count": e.column_count}
                cosmos_expectation_result = []
                decision = None
                error_type = type(e).__name__
                error_message = str(e)
                if self.source.on_empty == "skip":
                    logger.warning("source %s is empty, skipped per on_empty=skip: %s", source.path, e)
                    action_result = ActionResult(
                        action=ActionName.IGNORE,
                        status=ActionStatus.SKIPPED,
                        dead_letter=None,
                        error=None,
                    )
                    error_type = None
                    error_message = None
                else:
                    logger.warning("source %s is empty and on_empty=fail: %s", source.path, e)
                    action_result = SourceObjectPolicy(on_failure_config=self.on_failure).plan_action(Decision.FAILED)
            except Exception as e:
                logger.exception("failed to process %s", source.path)
                read_duration_sec = None
                validation_duration_sec = None
                gx_result = None
                statistics = {}
                cosmos_expectation_result = []
                decision = None
                error_type = type(e).__name__
                error_message = str(e)
                action_result = (
                    SourceObjectPolicy(on_failure_config=self.on_failure).plan_action(Decision.FAILED)
                    if self.on_failure.mode == "any_failure"
                    else ActionResult(
                        action=ActionName.IGNORE, status=ActionStatus.SKIPPED, dead_letter=None, error=None
                    )
                )

            action_error = self._apply_action(action_result, source.path)
            if action_error is not None:
                error_type = type(action_error).__name__
                error_message = str(action_error)

            raw_gx_result = gx_result.describe_dict() if gx_result is not None else None
            source_object_results.append(
                SourceObjectResult(
                    status=RunObjectStatus.COMPLETED if error_type is None else RunObjectStatus.ABORTED,
                    source_object=source,
                    row_count=statistics.get("row_count"),
                    column_count=statistics.get("column_count"),
                    read_duration_sec=read_duration_sec,
                    validation_duration_sec=validation_duration_sec,
                    error_type=error_type,
                    error_message=error_message,
                    decision=decision,
                    expectations=cosmos_expectation_result,
                    action=action_result,
                    raw_gx_result=raw_gx_result,
                )
            )

        cosmos_decision = CosmosPolicy().decide(source_object_results=source_object_results)

        if all(result.status == RunObjectStatus.COMPLETED for result in source_object_results):
            run_status = RunStatus.COMPLETED
        elif all(result.status == RunObjectStatus.ABORTED for result in source_object_results):
            run_status = RunStatus.ABORTED
        else:
            run_status = RunStatus.PARTIAL
        cosmos_result = CosmosResult(
            run_id=f"{self.validation.contract.data_asset_name}-{self.engine.id}",
            run_ts=datetime.datetime.now(tz=datetime.UTC),
            results=source_object_results,
            run_status=run_status,
            decision=cosmos_decision,
        )

        logger.info("run %s finished: run_status=%s, decision=%s", cosmos_result.run_id, run_status, cosmos_decision)
        self._sink.write_sink(result=cosmos_result)
