from typing import Annotated

from pydantic import Field

from cosmos.sinks.base import BaseFileFormat, BaseTableFormat
from cosmos.sinks.bigquery import BigQuerySink
from cosmos.sinks.gcs import GCSSink
from cosmos.sinks.local import LocalSink

SinkConfig = Annotated[
    GCSSink | BigQuerySink | LocalSink,
    Field(discriminator="storage"),
]

__all__ = ["SinkConfig", "BigQuerySink", "GCSSink", "LocalSink", "BaseFileFormat", "BaseTableFormat"]
