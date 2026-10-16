# Getting started

!!! note "Work in progress"

    The runner that executes a config end to end is still being built, so this page only shows what
    a config looks like. It becomes a full walkthrough once a release can run one.

## A minimal config

This is the smallest config Pylos is designed to run. It validates every CSV that matches the
glob, moves any that fail to a dead-letter directory, and writes one JSON report per run.

```yaml title="example/configs/minimal.yml"
--8<-- "example/configs/minimal.yml"
```

`id` names the dataset and is part of every report row's identity. `engine` picks what reads the
data and runs the expectations, and `source` says where the data is. Under `validate`, the
`contract` lists the expectations and `on_failure` says what happens to a file that fails. `report`
lists where results are written.

[Failure policy](concepts/failure-policy.md) explains how a failed expectation becomes an action,
and [Reporting](concepts/reporting.md) covers what gets written.
