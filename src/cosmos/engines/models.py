from typing import Literal

from pydantic import BaseModel, Field

from cosmos.destination.models import DestinationConfig
from cosmos.gx.models import GXConfig
from cosmos.sources.models import SourceConfig


class ValidationFrameworkConfig(BaseModel):
    """Root configuration for the entire validation pipeline.

    Ties together the engine, source, GX validation, and destination
    into a single object parsed from the user's YAML file.

    Attributes:
        engine: The DataFrame engine used to load and process data.
        source: Configuration for the input data source.
        gx: Configuration for the Great Expectations validation workflow.
        destination: Configuration for the output sink. Optional.
    """

    engine: Literal["pandas", "spark", "sql"] = Field(
        description="The DataFrame engine used to load and process data."
    )
    source: SourceConfig = Field(description="Configuration for the input data source.")
    gx: GXConfig = Field(
        description="Configuration for the Great Expectations validation workflow."
    )
    destination: DestinationConfig | None = Field(
        default=None,
        description="Configuration for the output sink. Optional.",
    )
