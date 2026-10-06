from pathlib import Path
from typing import Literal

from cosmos.results import CosmosResult
from cosmos.sinks.base import BaseFileFormat


class LocalSink(BaseFileFormat):
    storage: Literal["local"]

    def _handle(self, result: CosmosResult) -> str:
        return result.model_dump_json()

    def write_sink(self, result: CosmosResult) -> None:

        if not isinstance(self.path, Path):
            directory = Path(self.path).resolve()

        if not directory.is_file():
            file_path = directory.joinpath(f"{result.run_id}.json")
        else:
            file_path = directory

        if not file_path.parent.exists():
            file_path.parent.mkdir(parents=True, exist_ok=True)

        with file_path.open("w", encoding="utf-8") as f:
            f.write(self._handle(result))
