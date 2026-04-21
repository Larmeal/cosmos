from typing import Any, Literal

from pydantic import BaseModel, Field


class ExpectationConfig(BaseModel):
    """Configuration for a single Great Expectations rule.

    Attributes:
        expectation_type: The name of the GX expectation (e.g., 'expect_column_values_to_not_be_null').
        kwargs: The arguments passed to the expectation. Must at least be an empty dictionary.
    """

    expectation_type: str
    kwargs: dict[str, Any] = Field(default_factory=dict)


class ExpectationSuiteConfig(BaseModel):
    """Configuration for the suite containing multiple expectations.

    Attributes:
        name: The name of the expectation suite.
        expectations: A dictionary of individual expectation configurations, keyed by their names.
    """

    name: str
    expectations: list[ExpectationConfig]


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

    datasource_name: str
    data_asset_name: str
    batch_definition_name: str
    expectation_suite_name: str
    checkpoint_name: str
    expectation_suite: ExpectationSuiteConfig


class SourceConfig(BaseModel):
    """Configuration for the input data source.

    Attributes:
        type: The storage backend type. Restricted to specific literal values.
        file_format: The format of the file (e.g., 'csv', 'parquet').
        file_path: The URI or local path to the data.
        options: Additional reading options (e.g., delimiter, header rules).
    """

    type: Literal["local", "aws", "gcp", "azure"]
    file_format: str
    file_path: str
    options: dict[str, Any] = Field(default_factory=dict)


class ValidationFrameworkConfig(BaseModel):
    """
    A configuration class for the entire system, encompassing both GX and source configurations.
    """

    engine: Literal["pandas", "spark", "sql"]
    gx: GXConfig
    source: SourceConfig
