"""End-to-end: what happens to the source file when validation fails.

Local storage, pandas engine, local file sink. The report is checked against the
filesystem, so a report that claims a move cannot pass if the file did not move.
"""

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from cosmos.runner import Runner

pytestmark = pytest.mark.integration

MOCKED_CSV_NAME = "test-file.csv"

Workspace = dict[str, Path]
MakeRunner = Callable[..., Runner]
ReadReport = Callable[[], dict[str, Any]]


def test_failed_validation_moves_file_to_dead_letter(
    workspace: Workspace,
    make_runner: MakeRunner,
    read_report: ReadReport,
) -> None:
    """Data that fails a critical expectation: object completes, decision FAILED, file is acted on."""
    (workspace["source"] / MOCKED_CSV_NAME).write_text("id,name\n1,a\n,b\n", encoding="utf-8")

    make_runner().run()
    report = read_report()

    [obj] = report["results"]
    assert obj["status"] == "completed"
    assert obj["decision"] == "failed"
    assert obj["action"]["action"] == "move"
    assert obj["action"]["status"] == "completed"
    assert report["decision"] == "failed"

    # The report claims the file moved: check the filesystem agrees.
    assert not (workspace["source"] / MOCKED_CSV_NAME).exists()
    assert (workspace["dead_letter"] / MOCKED_CSV_NAME).is_file()


def test_failed_validation_with_ignore_leaves_file_in_place(
    workspace: Workspace,
    make_runner: MakeRunner,
    read_report: ReadReport,
) -> None:
    """Same bad data as above, but ``on_failure`` is overridden: the verdict is unchanged, the file is not touched."""
    (workspace["source"] / MOCKED_CSV_NAME).write_text("id,name\n1,a\n,b\n", encoding="utf-8")

    make_runner(on_failure={"action": "ignore"}).run()
    report = read_report()

    [obj] = report["results"]
    assert obj["decision"] == "failed"
    assert obj["action"]["action"] == "ignore"

    assert (workspace["source"] / MOCKED_CSV_NAME).is_file()
    assert not workspace["dead_letter"].exists()
