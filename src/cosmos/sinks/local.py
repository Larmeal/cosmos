from typing import Literal

from cosmos.sinks.base import BaseFileFormat


class LocalSink(BaseFileFormat):
    storage: Literal["local"]

    def handle(self) -> None:
        raise NotImplementedError("Handle method must be implemented by the subclass.")
