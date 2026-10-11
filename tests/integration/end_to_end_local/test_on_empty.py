"""End-to-end: ``source.on_empty`` when the glob matches no file at all.

Local storage, pandas engine, local file sink.
"""

from collections.abc import Callable
from pathlib import Path
from typing import Any, NamedTuple

import pytest

from cosmos.exceptions.data_error import SourceEmptyError
from cosmos.results import Decision, RunObjectStatus, RunStatus
from cosmos.runner import Runner
from tests.integration.end_to_end_local.test_on_failure import MOCKED_CSV_NAME

pytestmark = pytest.mark.integration

Workspace = dict[str, Path]
MakeRunner = Callable[..., Runner]
ReadReport = Callable[[], dict[str, Any]]


class Case(NamedTuple):
    """One source file and the whole report it must produce.

    The expected report starts as "the file was read and passed every expectation"
    (see ``_expected_report``). A case only states how it differs from that:

    Attributes:
        content: Bytes written to the source file.
        source_config: Overrides for the ``source`` block, e.g. ``{"on_empty": "fail"}``.
        on_failure_config: Overrides for the ``on_failure`` block.
        rows: Data rows in ``content``, used for the expectation's ``element_count``.
        expected_result: Fields of ``results[0]`` that differ from the default.
        expected_run: Run-level fields that differ from the default.
    """

    content: bytes
    source_config: dict[str, Any]
    rows: int
    expected_result: dict[str, Any]
    expected_run: dict[str, Any]


CASES_HAS_ONLY_HEADERS = [
    pytest.param(
        Case(
            content=b"id,name\n",
            source_config={"on_empty": "skip"},
            rows=0,
            expected_result={
                "error_type": None,
                "status": RunObjectStatus.COMPLETED,
                "decision": None,
            },
            expected_run={
                "run_status": RunStatus.COMPLETED,
                "decision": None,
            },
        ),
        id="has_only_headers_and_on_empty_skip",
    ),
    pytest.param(
        Case(
            content=b"id,name\n",
            source_config={"on_empty": "fail"},
            rows=0,
            expected_result={
                "error_type": SourceEmptyError.__name__,
                "status": RunObjectStatus.ABORTED,
                "decision": Decision.FAILED,
            },
            expected_run={
                "run_status": RunStatus.ABORTED,
                "decision": Decision.FAILED,
            },
        ),
        id="has_only_headers_and_on_empty_fail",
    ),
]

CASES_ZERO_BYTES = [
    pytest.param(
        Case(
            content=b"id,name\n",
            source_config={"on_empty": "skip"},
            rows=0,
            expected_result={},
            expected_run={},
        ),
        id="zero_bytes_and_on_empty_skip",
    ),
    pytest.param(
        Case(
            content=b"id,name\n",
            source_config={"on_empty": "fail"},
            rows=0,
            expected_result={},
            expected_run={},
        ),
        id="zero_bytes_and_on_empty_fail",
    ),
]

# What the report looks like for the "normal" case (the dict built by `_expected_report`).
# {
#   "cosmos_version": "0.1.0",
#   "run_id": "orders-test-end-to-end-local",
#   "run_ts": "2026-10-10T16:13:45.034915Z",
#   "results": [
#     {
#       "status": RunObjectStatus.COMPLETED,
#       "source_object": {
#         "path": ".../source/test-file.csv",
#         "size_bytes": 16,
#         "created_at": "2026-10-10T16:13:44.990000Z",
#         "modified_at": "2026-10-10T16:13:44.996910Z",
#         "metadata": {}
#       },
#       "row_count": 2,
#       "column_count": 2,
#       "read_duration_sec": 0.0017306999943684787,
#       "validation_duration_sec": 0.03437090000079479,
#       "error_type": null,
#       "error_message": null,
#       "decision": Decision.PASSED,
#       "expectations": [
#         {
#           "success": true,
#           "expectation_name": null,
#           "expectation_type": "expect_column_values_to_not_be_null",
#           "expectation_key": "8aa21df4ef85b66523329aa39fa9aa20ff07ff3d64b51157a75fa7250445e9c6",
#           "expectation_kwargs": {"column": "id"},
#           "description": null,
#           "severity": Severity.CRITICAL,
#           "element_count": 2,
#           "observed_value": null,
#           "unexpected_count": 0,
#           "unexpected_percent": 0.0,
#           "unexpected_values": [],
#           "unexpected_index": [],
#           "raised_exception": false,
#           "exception_message": null,
#           "meta": {"expectation_key": "8aa21df4ef85b66523329aa39fa9aa20ff07ff3d64b51157a75fa7250445e9c6"},
#           "notes": null
#         }
#       ],
#       "action": {
#         "action": ActionName.IGNORE,
#         "status": ActionStatus.SKIPPED,
#         "dead_letter": null,
#         "error": null
#       }
#     }
#   ],
#   "run_status": RunStatus.COMPLETED,
#   "decision": Decision.PASSED
# }


@pytest.mark.parametrize("case", CASES_HAS_ONLY_HEADERS)
def test_header_only_source_outcome_follows_on_empty(
    workspace: Workspace,
    make_runner: MakeRunner,
    read_report: ReadReport,
    case: Case,
) -> None:

    source_file = workspace["source"] / MOCKED_CSV_NAME
    source_file.write_bytes(case.content)

    make_runner(on_empty=case.source_config["on_empty"]).run()
    report = read_report()

    assert report["results"][0]["error_type"] == case.expected_result["error_type"]
    assert report["results"][0]["status"] == case.expected_result["status"]
    assert report["results"][0]["decision"] == case.expected_result["decision"]
    assert report["decision"] == case.expected_run["decision"]
    assert report["run_status"] == case.expected_run["run_status"]


@pytest.mark.parametrize("case", CASES_ZERO_BYTES)
def test_zero_byte_source_is_aborted_with_source_empty_error(
    workspace: Workspace,
    make_runner: MakeRunner,
    read_report: ReadReport,
    case: Case,
) -> None:

    source_file = workspace["source"] / MOCKED_CSV_NAME
    source_file.write_bytes(case.content)

    make_runner(on_empty=case.source_config["on_empty"]).run()

    report = read_report()

    print(report)

    assert report["results"][0]["error_type"] == SourceEmptyError.__name__
    assert report["results"][0]["status"] == RunObjectStatus.ABORTED
