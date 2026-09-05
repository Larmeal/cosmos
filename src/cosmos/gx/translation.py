import logging
from typing import Any

from great_expectations.core.expectation_validation_result import (
    ExpectationSuiteValidationResult,
)

from cosmos.gx.models import ExpectationConfig
from cosmos.results import ExpectationResult

logger = logging.getLogger(__name__)


class GXTranslateExpectationResult:
    def __init__(self, validation_config: list[ExpectationConfig], gx_result: ExpectationSuiteValidationResult) -> None:
        self.validation_config = validation_config
        self.gx_result = gx_result
        self.cosmos_expectation_result: list[ExpectationResult] = []

    def _mapping_expectation_config(self, expectation_key: str) -> ExpectationConfig:
        for config in self.validation_config:
            if config.expectation_key == expectation_key:
                return config
        raise ValueError(f"ExpectationConfig with key {expectation_key!r} not found.")

    def translate(self) -> list[ExpectationResult]:  # type: ignore

        if not self.gx_result.get("results"):
            raise ValueError("No results found in the Great Expectations validation result.")

        for result in self.gx_result.get("results"):  # type: ignore
            result: dict

            expectation_config_data: dict[str, Any] | None = result.get("expectation_config")
            meta: dict[str, Any] = (expectation_config_data or {}).get("meta") or {}

            expectation_key = meta.get("expectation_key")
            if expectation_key is None:
                raise ValueError(
                    "Missing 'expectation_key' in the GX result's 'expectation_config.meta'. COSMOS "
                    "always injects this key into the expectation's meta before validation, so its "
                    "absence here means Great Expectations did not echo it back as expected — this is "
                    "a bug in the COSMOS framework, please report it to the maintainers."
                )
            expectation_config: ExpectationConfig = self._mapping_expectation_config(expectation_key)

            expectation_name = expectation_config.name
            expectation_type = expectation_config.expectation_type
            expectation_kwargs = expectation_config.kwargs
            description = expectation_config.description
            severity = expectation_config.severity

            result_data: dict[str, Any] | None = result.get("result")
            exception_info = result.get("exception_info")

            success: bool = result.get("success")  # type: ignore
            element_count: int | None = result_data.get("element_count") if result_data else None
            observed_value: Any | None = result_data.get("observed_value") if result_data else None
            unexpected_count: int | None = result_data.get("unexpected_count") if result_data else None
            unexpected_percent: float | None = result_data.get("unexpected_percent") if result_data else None
            unexpected_values: list[Any] | None = result_data.get("partial_unexpected_list") if result_data else None
            unexpected_index: list[int] | None = (
                result_data.get("partial_unexpected_index_list") if result_data else None
            )

            raised_exception: bool = exception_info.get("raised_exception") if exception_info else False
            exception_message: str | None = exception_info.get("exception_message") if exception_info else None
            raw_notes: str | list[str] | None = (
                expectation_config_data.get("notes") if expectation_config_data else None
            )
            notes: str | None = "\n".join(raw_notes) if isinstance(raw_notes, list) else raw_notes
            self.cosmos_expectation_result.append(
                ExpectationResult(
                    expectation_key=expectation_key,
                    expectation_name=expectation_name,
                    expectation_type=expectation_type,
                    expectation_kwargs=expectation_kwargs,
                    description=description,
                    severity=severity,
                    success=success,
                    element_count=element_count,
                    observed_value=observed_value,
                    unexpected_count=unexpected_count,
                    unexpected_percent=unexpected_percent,
                    unexpected_values=unexpected_values,
                    unexpected_index=unexpected_index,
                    raised_exception=raised_exception,
                    exception_message=exception_message,
                    meta=meta,
                    notes=notes,
                )
            )

    def get_result(self) -> list[ExpectationResult]:
        return self.cosmos_expectation_result
