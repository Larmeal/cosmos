from typing import Any, Literal

from pydantic import BaseModel, Field


class ExpectationConfig(BaseModel):
    """Configuration for a single Great Expectations rule.

    Attributes:
        expectation_type: The name of the GX expectation.
        kwargs: The arguments passed to the expectation.
        meta: Additional custom metadata for the expectation.
        notes: Free-form text notes for data documentation.
        description: A clear description of why this rule exists.
        severity: The severity level if this expectation fails.
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
    severity: Literal["critical", "warning", "info"] = Field(
        default="warning",
        description="Determines the pipeline behavior if this expectation fails.",
    )


class ExpectationSuiteConfig(BaseModel):
    """Configuration for the suite containing multiple expectations.

    Attributes:
        name: The name of the expectation suite.
        expectations: A list of individual expectation configurations.
    """

    name: str = Field(description="The name of the expectation suite.")
    expectations: list[ExpectationConfig] = Field(description="A list of individual expectation configurations.")


class GXConfig(BaseModel):
    """The master configuration for the Great Expectations context.

    Attributes:
        datasource_name: The name of the GX datasource.
        data_asset_name: The name of the data asset.
        batch_definition_name: The name of the batch definition (V1.x architecture).
        expectation_suite_name: The name used to register the suite.
        checkpoint_name: The name of the validation checkpoint.
        expectation_suite: The nested suite configuration.
    """

    datasource_name: str | None = Field(default=None, description="The name of the GX datasource.")
    data_asset_name: str = Field(description="The name of the data asset.")
    batch_definition_name: str | None = Field(
        default=None,
        description="The name of the batch definition (V1.x architecture).",
    )
    expectation_suite_name: str | None = Field(default=None, description="The name used to register the suite.")
    checkpoint_name: str | None = Field(default=None, description="The name of the validation checkpoint.")
    expectation_suite: ExpectationSuiteConfig = Field(
        description="The nested expectation suite configuration containing all expectations."
    )
