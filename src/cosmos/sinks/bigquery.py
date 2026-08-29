from typing import Literal

from cosmos.sinks.base import BaseTableFormat


class BigQuerySink(BaseTableFormat):
    storage: Literal["bigquery"]

    def handle(self) -> None:
        raise NotImplementedError("Handle method must be implemented by the subclass.")
