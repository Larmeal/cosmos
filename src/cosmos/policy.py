from cosmos.actions import IgnoreFailureAction, OnFailureActionConfig, RelocateFailureAction
from cosmos.results import ActionName, ActionResult, ActionStatus, Decision, ExpectationResult, Severity


class Policy:
    """Decides what a validation result means, and what should happen to the file.

    Given the expectations checked against one source object, Policy answers the
    two questions the rest of the run needs:

        "was the data good?"       -> Decision.PASS / WARN / FAIL
        "what do we do about it?"  -> an ActionResult naming the action to perform

    Severity is what connects the two. A failure matters only as much as the
    contract said it should:

        a critical expectation failed  -> FAIL, and the configured on_failure
                                          action fires (move, copy, delete)
        only warnings failed           -> WARN, the file is left where it is
        nothing failed, or only info   -> PASS, the file is left where it is

    Only FAIL ever touches the file. WARN and PASS are still written to the
    report; they just do not move anything.

    Policy is a brain with no hands. It never opens a file, relocates one, or
    writes a report. It produces the two verdicts above and hands them back, and
    the runner is what performs the action and records how it went. That is what
    lets this class be tested with nothing but a list of fabricated
    ``ExpectationResult`` objects: no GX, no storage, no engine, no I/O.

    It also looks at one source object at a time and never at its neighbours. The
    run-level verdicts (``run_status``, ``data_decision``) are rollups computed
    over every object after the loop finishes, not something Policy produces.

    Attributes:
        on_failure_config: What the config said to do with a file that fails.
        decision_result: Filled by ``decide()``, ``None`` until it runs.
        action_result: Filled by ``decide()``, ``None`` until it runs. Its status
            starts at ``PENDING`` because the report records the intent before the
            action actually runs, so a row still sitting at ``PENDING`` afterwards
            means the process died in between.
    """

    def __init__(self, on_failure_config: OnFailureActionConfig) -> None:
        self.on_failure_config = on_failure_config
        self.decision_result: Decision | None = None
        self.action_result: ActionResult | None = None

    def _make_decision(self, expectation_results: list[ExpectationResult]) -> Decision:
        """Applies the severity rule to one object's expectation results.

        Only failures are considered, and the worst severity among them wins. An
        ``info`` expectation that fails changes nothing: it is recorded, but it
        does not lift the verdict above ``PASS``.
        """
        failures = [result for result in expectation_results if not result.success]

        if any(result.severity == Severity.CRITICAL for result in failures):
            return Decision.FAIL
        if any(result.severity == Severity.WARNING for result in failures):
            return Decision.WARN
        return Decision.PASS

    def decide(self, expectation_results: list[ExpectationResult]) -> None:
        """Works out the verdict and the action, and stores both on the instance.

        Nothing is read, written or relocated here. Once this returns,
        ``decision_result`` and ``action_result`` hold the answers for the runner
        to record and act on.

        Args:
            expectation_results: Every expectation checked against this one source
                object, as produced by ``gx/``.
        """
        self.decision_result = self._make_decision(expectation_results)
        decision_result = self.decision_result

        if isinstance(self.on_failure_config, RelocateFailureAction):
            dead_letter = self.on_failure_config.dead_letter
        else:
            dead_letter = None

        if decision_result == Decision.FAIL and not isinstance(self.on_failure_config, IgnoreFailureAction):
            self.action_result = ActionResult(
                action=self.on_failure_config.action,
                status=ActionStatus.PENDING,
                dead_letter=dead_letter,
                error=None,
            )
        else:
            self.action_result = ActionResult(
                action=ActionName.IGNORE,
                status=ActionStatus.SKIPPED,
                dead_letter=None,
                error=None,
            )
