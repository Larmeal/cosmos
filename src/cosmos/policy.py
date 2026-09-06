from cosmos.actions import IgnoreFailureAction, OnFailureActionConfig, RelocateFailureAction
from cosmos.results import ActionName, ActionResult, ActionStatus, Decision, ExpectationResult, Severity


class Policy:
    def __init__(self, on_failure_config: OnFailureActionConfig) -> None:
        self.on_failure_config = on_failure_config

    def _make_decision(self, expectation_results: list[ExpectationResult]) -> Decision:
        failures = [result for result in expectation_results if not result.success]

        if any(result.severity == Severity.CRITICAL for result in failures):
            return Decision.FAIL
        if any(result.severity == Severity.WARNING for result in failures):
            return Decision.WARN
        return Decision.PASS

    def decide(self, expectation_results: list[ExpectationResult]) -> tuple[Decision, ActionResult]:
        decision_result = self._make_decision(expectation_results)

        if isinstance(self.on_failure_config, RelocateFailureAction):
            dead_letter = self.on_failure_config.dead_letter
        else:
            dead_letter = None

        if decision_result == Decision.FAIL and not isinstance(self.on_failure_config, IgnoreFailureAction):
            return decision_result, ActionResult(
                action=self.on_failure_config.action,
                status=ActionStatus.PENDING,
                dead_letter=dead_letter,
                error=None,
            )
        else:
            return decision_result, ActionResult(
                action=ActionName.IGNORE,
                status=ActionStatus.SKIPPED,
                dead_letter=None,
                error=None,
            )
