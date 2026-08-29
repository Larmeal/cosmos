from typing import Literal

from cosmos.sinks.base import BaseFileFormat


class GCSSink(BaseFileFormat):
    storage: Literal["gcs"]

    def handle(self) -> None:
        raise NotImplementedError("Handle method must be implemented by the subclass.")
