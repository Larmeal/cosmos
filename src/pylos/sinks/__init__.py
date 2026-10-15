from typing import Annotated

from pydantic import Field

from pylos.sinks.base import BaseFileFormat, BaseTableFormat
from pylos.sinks.bigquery import BigQuerySink
from pylos.sinks.gcs import GCSSink
from pylos.sinks.local import LocalSink

SinkConfig = Annotated[
    GCSSink | BigQuerySink | LocalSink,
    Field(discriminator="storage"),
]

__all__ = ["SinkConfig", "BigQuerySink", "GCSSink", "LocalSink", "BaseFileFormat", "BaseTableFormat"]
