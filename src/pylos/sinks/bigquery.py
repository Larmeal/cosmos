from typing import Literal

from pylos.sinks.base import BaseTableFormat


class BigQuerySink(BaseTableFormat):
    """Report sink for a BigQuery table. Not implemented yet; planned for v0.2.

    It does not implement ``_handle`` or ``write_sink`` yet, so a config with
    ``report.storage: bigquery`` fails at load with ``TypeError: Can't instantiate
    abstract class``.
    """

    storage: Literal["bigquery"]

    def handle(self) -> None:
        """Placeholder that always raises ``NotImplementedError``. Not part of the ``BaseSink`` interface."""
        raise NotImplementedError("Handle method must be implemented by the subclass.")
