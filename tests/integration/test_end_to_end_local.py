"""End-to-end: run COSMOS against local fixture files, assert the CosmosResult.

Organised by scenario, not by module. Mark slow / external cases with
``@pytest.mark.integration`` so ``pytest -m "not integration"`` stays fast.
"""
