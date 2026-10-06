from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from great_expectations import Checkpoint, ExpectationSuite, ValidationDefinition
from great_expectations.core.expectation_validation_result import (
    ExpectationSuiteValidationResult,
)
from great_expectations.data_context.data_context.ephemeral_data_context import EphemeralDataContext
from great_expectations.data_context.data_context.file_data_context import FileDataContext
from great_expectations.expectations.expectation_configuration import (
    ExpectationConfiguration,
)
from great_expectations.expectations.metadata_types import FailureSeverity

from cosmos.gx.models import GXConfig

if TYPE_CHECKING:
    from great_expectations.data_context.store.store import (
        DataDocsSiteConfigTypedDict,
    )
    from great_expectations.data_context.types.resource_identifiers import ValidationResultIdentifier

logger = logging.getLogger(__name__)


class GXValidator:
    """Base class for GX validators. Defines the interface for validation."""

    def __init__(self, config: GXConfig) -> None:
        self.context: EphemeralDataContext | FileDataContext
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
                ),
                match_type="success",
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

    def _get_context(self, mode: Literal["ephemeral", "file"]) -> EphemeralDataContext | FileDataContext:
        """Initializes and returns a GX context."""
        from great_expectations import get_context

        if mode == "file":
            return get_context(mode=mode, context_root_dir=Path(self.config.data_docs.store_path).joinpath("gx"))
        return get_context(mode=mode)

    def _build_document(self, context: FileDataContext, resource_identifiers: list[ValidationResultIdentifier]) -> None:
        """Builds the GX data documentation."""

        site_name = f"{self._data_asset_name}_site"

        if self.config.data_docs.store_path:
            site_config: DataDocsSiteConfigTypedDict = {
                "class_name": "SiteBuilder",
                "site_index_builder": {
                    "class_name": "DefaultSiteIndexBuilder",
                    "validation_results_limit": 100,
                },
                "store_backend": {
                    "class_name": "TupleFilesystemStoreBackend",
                    "base_directory": self.config.data_docs.store_path,
                },
            }

        if site_name in context.list_data_docs_sites():
            context.update_data_docs_site(
                site_name=site_name,
                site_config=site_config,
            )
        else:
            context.add_data_docs_site(
                site_name=site_name,
                site_config=site_config,
            )

        context.build_data_docs(resource_identifiers=resource_identifiers)

    def validate(self, df: Any) -> ExpectationSuiteValidationResult:
        """Validates the DataFrame and returns the result dictionary."""
        dataset = self.config.contract.data_asset_name
        logger.info(f"Starting GX validation for dataset: {dataset}")

        if self.config.data_docs.enabled:
            self.context = self._get_context(
                mode="file",
            )
        else:
            self.context = self._get_context(mode="ephemeral")

        data_source = self.context.data_sources.add_or_update_pandas(name=self._datasource_name)
        data_asset = data_source.add_dataframe_asset(name=self._data_asset_name)
        batch_definition = data_asset.add_batch_definition_whole_dataframe(
            name=self._batch_definition_name,  # type: ignore
        )

        batch_parameters = {"dataframe": df}
        suite = self.context.suites.add_or_update(self.expectation_suites)

        validation_definition = self.context.validation_definitions.add_or_update(
            ValidationDefinition(name=f"{self._expectation_suite_name}_validation", data=batch_definition, suite=suite)
        )
        checkpoint = self.context.checkpoints.add_or_update(
            Checkpoint(
                name=f"{self._expectation_suite_name}_checkpoint", validation_definitions=[validation_definition]
            )
        )
        checkpoint_result = checkpoint.run(batch_parameters=batch_parameters)
        validation_result_identifier, gx_result = next(iter(checkpoint_result.run_results.items()))

        if isinstance(self.context, FileDataContext):
            self._build_document(self.context, resource_identifiers=[validation_result_identifier])

        return gx_result
