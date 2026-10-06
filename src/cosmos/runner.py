from __future__ import annotations

import datetime
from collections.abc import Callable, Generator
from contextlib import contextmanager
from time import perf_counter
from typing import TYPE_CHECKING

from cosmos.engines import Engine
from cosmos.gx.translation import GXTranslateExpectationResult
from cosmos.gx.validator import GXValidator
from cosmos.policy import CosmosPolicy, SourceObjectPolicy
from cosmos.results import (
    ActionName,
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

    @contextmanager
    def _timer(self) -> Generator[Callable[[], float]]:
        start = perf_counter()
        yield lambda: perf_counter() - start

    def run(self) -> None:
        source_object_metadata: list[SourceObjectMetadata] = self.storage.glob(self.engine.source.file_path)

        source_object_results: list[SourceObjectResult] = []
        for source in source_object_metadata:
            source: SourceObjectMetadata

            try:
                with self._timer() as duration:
                    data = self.engine.load_data(file_path=source.path)

                read_duration_sec = duration()
                statistics = self.engine.statistics(data=data)

                with self._timer() as validation_duration:
                    gx_result = GXValidator(config=self.validation).validate(df=data)

                validation_duration_sec = validation_duration()

                cosmos_expectation_result = GXTranslateExpectationResult(
                    validation_config=self.validation.contract.expectations,
                ).translate(gx_result=gx_result)

                decision, action_result = SourceObjectPolicy(on_failure_config=self.on_failure).decide(
                    expectation_results=cosmos_expectation_result
                )

                if action_result.action != ActionName.IGNORE:
                    self.on_failure.handle(src=source.path)
                    action_result.status = ActionStatus.COMPLETED
            except Exception as e:
                read_duration_sec = None
                validation_duration_sec = None
                gx_result = None
                statistics = {}
                cosmos_expectation_result = []
                decision = Decision.WARNED
                action_result = None
                error_type = type(e).__name__
                error_message = str(e)
            else:
                error_type = None
                error_message = None
            finally:
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
                        raw_gx_result=raw_gx_result,  # type: ignore
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

        self._sink.write_sink(result=cosmos_result)
