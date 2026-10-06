"""Tests for cosmos.sinks.local: writing the run report to the local filesystem."""

import json
from pathlib import Path

from cosmos.results import CosmosResult
from cosmos.sinks.local import LocalSink


def test_write_sink_creates_missing_directory(
    tmp_path: Path,
    cosmos_result: CosmosResult,
) -> None:
    target_dir = tmp_path / "reports"
    sink = LocalSink(storage="local", format="file", path=str(target_dir))

    sink.write_sink(cosmos_result)

    assert target_dir.parent.is_dir()


def test_write_sink_names_file_after_run_id(
    tmp_path: Path,
    cosmos_result: CosmosResult,
) -> None:
    sink = LocalSink(storage="local", format="file", path=str(tmp_path))

    sink.write_sink(cosmos_result)

    assert (tmp_path / f"{cosmos_result.run_id}.json").exists()


def test_write_sink_writes_full_result_as_json(
    tmp_path: Path,
    cosmos_result: CosmosResult,
) -> None:
    sink = LocalSink(storage="local", format="file", path=str(tmp_path))

    sink.write_sink(cosmos_result)

    written = json.loads((tmp_path / f"{cosmos_result.run_id}.json").read_text(encoding="utf-8"))
    assert written == json.loads(cosmos_result.model_dump_json())
