from cosmos.actions import IgnoreFailureAction, OnFailureActionConfig, RelocateFailureAction
from cosmos.results import ActionName, ActionResult, ActionStatus, Decision, ExpectationResult, Severity


class Policy:
    """Decides what a validation result means, and what should happen to the file.

    Given the expectations checked against one source object, Policy answers the
    two questions the rest of the run needs:

        "was the data good?"       -> Decision.PASS / WARN / FAIL
        "what do we do about it?"  -> an ActionResult naming the action to perform

    Severity connects the two: a failure matters only as much as the contract
    said it should.

        a critical expectation failed  -> FAIL, and the configured on_failure
                                          action is planned (move, copy, delete)
        only warnings failed           -> WARN, the file is left where it is
        nothing failed, or only info   -> PASS, the file is left where it is

    Only FAIL ever touches the file. WARN and PASS are still written to the
    report; they just do not move anything.

    Policy is a brain with no hands. It never opens a file, relocates one, or
    writes a report, and it keeps no per-object state: ``decide()`` takes one
    object's results and returns the verdicts rather than storing them, so one
    instance is built per run and reused, unchanged, for every object in it.
    That is what lets this class be tested with nothing but a list of fabricated
    ``ExpectationResult`` objects: no GX, no storage, no engine, no I/O.

    The ``ActionResult`` it returns is only an intent: status is ``PENDING`` for
    an action that will run, ``SKIPPED`` when there is nothing to do. The report
    records that intent before the runner acts, so a row still at ``PENDING``
    afterwards means the process died in between.

    Policy looks at one source object at a time, never at its neighbours. The
    run-level verdicts (``run_status``, ``decision``) are rollups computed over
    every object after the loop finishes, not something Policy produces.

    Attributes:
        on_failure_config: What the config said to do with a file that fails.
    """

    def __init__(self, on_failure_config: OnFailureActionConfig) -> None:
        self.on_failure_config = on_failure_config

    def _make_decision(self, expectation_results: list[ExpectationResult]) -> Decision:
        """Reduces one object's expectation results to a verdict by worst severity.

        Only failures count, and a failed ``info`` expectation never lifts the
        verdict above ``PASS``: it is recorded, but it exists to leave a note for
        a person, not to gate anything.
        """
        failures = [result for result in expectation_results if not result.success]

        if any(result.severity == Severity.CRITICAL for result in failures):
            return Decision.FAIL
        if any(result.severity == Severity.WARNING for result in failures):
            return Decision.WARN
        return Decision.PASS

    def _plan_action(self, decision_result: Decision) -> ActionResult:
        """Derives the unexecuted action from the verdict and ``on_failure_config``.

        Only ``FAIL`` leads to a real action, and only when the config is not
        ``IgnoreFailureAction``; every other case returns ``IGNORE`` / ``SKIPPED``
        because nothing touches the file. The runner is what performs a
        ``PENDING`` action and updates its status afterwards.
        """
        if decision_result == Decision.FAIL and not isinstance(self.on_failure_config, IgnoreFailureAction):
            dead_letter = (
                self.on_failure_config.dead_letter
                if isinstance(self.on_failure_config, RelocateFailureAction)
                else None
            )
            return ActionResult(
                action=self.on_failure_config.action,
                status=ActionStatus.PENDING,
                dead_letter=dead_letter,
                error=None,
            )

        return ActionResult(
            action=ActionName.IGNORE,
            status=ActionStatus.SKIPPED,
            dead_letter=None,
            error=None,
        )

    def decide(self, expectation_results: list[ExpectationResult]) -> tuple[Decision, ActionResult]:
        """Turns one source object's expectation results into its two verdicts.

        This is the only method the rest of COSMOS calls; the two helpers exist
        to support it. Nothing is read, written or relocated here. The runner
        records the decision and then performs the action if one is due.

        Args:
            expectation_results: Every expectation checked against this one source
                object, as produced by ``gx/``.

        Returns:
            The ``Decision`` for the object and the ``ActionResult`` the runner
            should carry out. Neither is stored on ``self``.
        """
        decision_result = self._make_decision(expectation_results)
        action_result = self._plan_action(decision_result)

        return decision_result, action_result
