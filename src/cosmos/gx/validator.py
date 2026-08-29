from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from great_expectations import ExpectationSuite
from great_expectations.core.expectation_validation_result import ExpectationSuiteValidationResult
from great_expectations.expectations.expectation_configuration import (
    ExpectationConfiguration,
)
from great_expectations.expectations.metadata_types import FailureSeverity

from cosmos.gx.models import GXConfig

if TYPE_CHECKING:
    from great_expectations.data_context.data_context.ephemeral_data_context import EphemeralDataContext

logger = logging.getLogger(__name__)


class GXValidator:
    """Base class for GX validators. Defines the interface for validation."""

    def __init__(self, config: GXConfig) -> None:
        self.context: EphemeralDataContext
        self.config: GXConfig = config
        self._datasource_name = self.config.contract.datasource_name
        self._data_asset_name = self.config.contract.data_asset_name
        self._batch_definition_name = self.config.contract.batch_definition_name
        self._expectation_suite_name = self.config.contract.expectation_suite_name
        self._expectation_suites = self.expectation_suites

    @property
    def expectation_suites(self) -> ExpectationSuite:
        """Constructs an ExpectationSuite from the GXConfig."""
        suite = ExpectationSuite(name=self._expectation_suite_name)
        for exp_cfg in self.config.contract.expectations:
            suite.add_expectation_configuration(
                ExpectationConfiguration(
                    type=exp_cfg.expectation_type,
                    kwargs=exp_cfg.kwargs,
                    meta=exp_cfg.meta,
                    notes=exp_cfg.notes,
                    description=exp_cfg.description,
                    severity=self._map_severity(exp_cfg.severity),
                )
            )
        return suite

    @staticmethod
    def _map_severity(severity_str: str) -> FailureSeverity:
        """Converts the string severity from YAML to GX FailureSeverity Enum."""

        match severity_str.lower():
            case "critical":
                return FailureSeverity.CRITICAL
            case "warning":
                return FailureSeverity.WARNING
            case "info":
                return FailureSeverity.INFO
            case _:
                return FailureSeverity.CRITICAL

    def _get_context(self) -> Any:  # noqa: ANN401
        """Initializes and returns a GX context."""
        from great_expectations import get_context

        return get_context(mode="ephemeral")

    def validate(self, df: Any) -> ExpectationSuiteValidationResult:  # noqa: ANN401
        """Validates the DataFrame and returns the result dictionary."""
        dataset = self.config.contract.data_asset_name
        logger.info(f"Starting GX validation for dataset: {dataset}")

        self.context: EphemeralDataContext = self._get_context()
        data_source = self.context.data_sources.add_pandas(name=self._datasource_name)
        data_asset = data_source.add_dataframe_asset(name=self._data_asset_name)
        batch_definition = data_asset.add_batch_definition_whole_dataframe(
            name=self._batch_definition_name,
        )

        batch_parameters = {"dataframe": df}
        batch = batch_definition.get_batch(batch_parameters=batch_parameters)

        suite = self.context.suites.add(self.expectation_suites)
        return batch.validate(suite)
