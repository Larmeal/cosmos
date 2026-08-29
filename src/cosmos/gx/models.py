from typing import Any, Literal, Self

from pydantic import BaseModel, Field, model_validator


class ExpectationConfig(BaseModel):
    """Configuration for a single Great Expectations rule.

    Attributes:
        expectation_type: The name of the GX expectation.
        kwargs: The arguments passed to the expectation.
        meta: Additional custom metadata for the expectation.
        notes: Free-form text notes for data documentation.
        description: A clear description of why this rule exists.
        name: An optional stable key for this rule, used in reports.
        severity: The severity level if this expectation fails. Required.
    """

    expectation_type: str = Field(
        description="The name of the GX expectation (e.g., 'expect_column_values_to_not_be_null')."
    )
    kwargs: dict[str, Any] = Field(
        default_factory=dict,
        description="The keyword arguments passed to the expectation (e.g., {'column': 'id'}).",
    )
    meta: dict[str, Any] | None = Field(
        default=None,
        description="Additional custom metadata for the expectation (e.g., {'data_quality_issue': 'completeness'}).",
    )
    notes: str | list[str] | None = Field(
        default=None,
        description="Free-form text notes for data documentation.",
    )
    description: str | None = Field(
        default=None,
        description="A clear description of why this rule exists.",
    )
    name: str | None = Field(
        default=None,
        description="An optional name for the expectation. If not provided, a default name will be generated.",
    )
    severity: Literal["critical", "warning", "info"] = Field(
        default="critical",
        description=(
            "The severity level if this expectation fails. 'critical' triggers the failure action, 'warning' and 'info' are recorded only. Defaults to 'critical'."
        ),
    )


class ContractConfig(BaseModel):
    """The contract for a dataset: the rules it must satisfy.

    Attributes:
        data_asset_name: The contract's name, written as `name:` in YAML.
        description: A description of the contract's purpose.
        expectations: The rules to apply to every source object.
    """

    data_asset_name: str = Field(description="The name of the data asset.", alias="name")
    datasource_name: str | None = Field(
        default=None,
        description="The name of the GX datasource.",
    )
    batch_definition_name: str | None = Field(
        default=None,
        description="The name of the batch definition (V1.x architecture).",
    )
    expectation_suite_name: str | None = Field(
        default=None,
        description="The name used to register the suite.",
    )
    description: str | None = Field(
        default=None,
        description="A description of the contract's purpose.",
    )
    expectations: list[ExpectationConfig] = Field(
        description="The nested expectation suite configuration containing all expectations."
    )

    @model_validator(mode="after")
    def _resolve_gx_names(self) -> Self:
        self.datasource_name = self.datasource_name or f"{self.data_asset_name}_source"
        self.batch_definition_name = self.batch_definition_name or f"{self.data_asset_name}_batch"
        self.expectation_suite_name = self.expectation_suite_name or f"{self.data_asset_name}_suite"
        return self


class DataDocsConfig(BaseModel):
    """Configuration for Great Expectations Data Docs.

    Attributes:
        enabled: Whether to render the site at all. Off by default.
        store_path: Where to write it. Nothing is persisted when omitted.
    """

    enabled: bool = Field(
        default=False,
        description="Indicates whether Data Docs generation is enabled.",
    )
    store_path: str | None = Field(
        default=None,
        description="The path where Data Docs will be stored. If not provided, a default path will be used.",
    )


class GXConfig(BaseModel):
    """The `validate:` section of the configuration.

    Attributes:
        contract: The rules to apply, and what each failure means.
        data_docs: Whether to render an HTML view of the results, and where.
    """

    contract: ContractConfig = Field(
        description="The contract for the dataset, including its expectations.",
    )
    data_docs: DataDocsConfig = Field(
        default_factory=DataDocsConfig,
        description="Configuration for Great Expectations Data Docs. Omitted means disabled.",
    )
