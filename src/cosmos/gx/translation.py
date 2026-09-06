import logging
from typing import Any

from great_expectations.core.expectation_validation_result import (
    ExpectationSuiteValidationResult,
)

from cosmos.gx.models import ExpectationConfig
from cosmos.results import ExpectationResult

logger = logging.getLogger(__name__)


class GXTranslateExpectationResult:
    """Turns one GX validation result into COSMOS's own ``ExpectationResult`` rows.

    This class is the proxy at the GX/COSMOS boundary: everything downstream of
    ``translate()`` (policy, sinks, reports) works only with COSMOS's own
    ``ExpectationResult`` model and never touches a GX object directly. That keeps
    every GX-specific detail (its nested result dict shape, the ``partial_``-prefixed
    keys, the fact that ``meta`` is the only field that survives a suite round trip)
    confined to this one class. When GX changes its result schema in a future
    version, the fix is a diff to ``translate()`` alone; nothing else in COSMOS has
    to know or care that GX changed at all.

    GX's result dict carries no COSMOS identifiers of its own: ``expectation_key``
    only survives the round trip through ``expectation_config.meta`` (GX regenerates
    its own ``id`` when a suite is added to a context, so that field can't be used).
    ``translate()`` matches each GX result back to the ``ExpectationConfig`` that
    produced it via that key, then rebuilds the fields COSMOS reports on, pulling
    some straight from our own config (name, type, kwargs, description, severity)
    and others from GX's result payload (success, counts, unexpected values).

    Attributes:
        validation_config: The expectations that were validated, used to look up
            each GX result's declared name/description/severity by its key.
        gx_result: The raw GX validation result (dict-like) for the whole suite.
        cosmos_expectation_result: Populated by ``translate()``; empty until then.
    """

    def __init__(self, validation_config: list[ExpectationConfig], gx_result: ExpectationSuiteValidationResult) -> None:
        self.validation_config = validation_config
        self.gx_result = gx_result
        self.cosmos_expectation_result: list[ExpectationResult] = []

    def _mapping_expectation_config(self, expectation_key: str) -> ExpectationConfig:
        """Finds the ``ExpectationConfig`` that declared the given key.

        Raises:
            ValueError: No expectation in ``validation_config`` has this key,
                meaning the GX result doesn't correspond to this contract.
        """
        for config in self.validation_config:
            if config.expectation_key == expectation_key:
                return config
        raise ValueError(f"ExpectationConfig with key {expectation_key!r} not found.")

    def translate(self) -> list[ExpectationResult]:  # type: ignore
        """Builds ``cosmos_expectation_result`` from ``gx_result``, one row per expectation.

        Raises:
            ValueError: ``gx_result`` has no ``results`` list, or one of its entries
                is missing ``expectation_key`` in ``expectation_config.meta``. The
                latter means COSMOS's own meta injection didn't survive validation,
                which is a framework bug rather than a user error.
        """

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
                    "absence here means Great Expectations did not echo it back as expected, which is "
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
        """Returns the rows built by ``translate()``, or an empty list if it hasn't run yet."""
        return self.cosmos_expectation_result
