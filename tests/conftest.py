"""Shared fixtures for the COSMOS test suite.

Fixtures defined here are available to every test under ``tests/`` without import.
Put cross-cutting factories here (sample Pydantic models, fake storage, etc.);
keep module-specific fixtures next to their test file.
"""

import datetime

import pytest

from cosmos.results import CosmosResult, RunStatus


@pytest.fixture
def cosmos_result() -> CosmosResult:
    """A minimal, valid CosmosResult: empty run, nothing to report."""
    return CosmosResult(
        run_id="test-run-id",
        run_ts=datetime.datetime(2024, 1, 1, tzinfo=datetime.UTC),
        results=[],
        run_status=RunStatus.COMPLETED,
        decision=None,
    )
