# Failure policy

Great Expectations tells you whether a batch passed. Pylos decides what that means for the file.

## From severity to action

Each expectation in a contract has a severity, and the severity of what failed sets the decision:

| What failed | Decision | What happens to the file |
|---|---|---|
| A `critical` expectation | `FAIL` | The configured `on_failure` action runs (move, copy or delete) |
| Only `warning` expectations | `WARN` | Left where it is |
| Nothing, or only `info` | `PASS` | Left where it is |

Only `FAIL` touches the file. All three outcomes are written to the report.

`on_failure` sits beside `validate:` instead of inside it, because it also fires for a file that
could not be read at all, before any expectation ran.

## Data problems and everything else

Pylos has two error classes:

```
PylosError
├── ConfigurationError   the declaration is wrong   -> abort the run
└── DataError            the data itself is bad     -> dead-letter this file, continue
```

A corrupt CSV and a network timeout both reach Pylos as an exception from the reader, and they call
for opposite responses. If both were treated as bad data, a network blip could quarantine ten
healthy files. The rule is:

> Positively identify a data problem. Treat everything else as fatal.

Only `DataError` is caught while Pylos loops over source objects. A timeout, an expired credential
or a bug in Pylos propagates and stops the run before anything is touched. See
[`pylos.exceptions`](../reference/exceptions/index.md) for the classes.

## Report first, file action second

Pylos works through each checkpoint in this order:

1. Read and validate each object.
2. Decide, per object.
3. Write the report to every sink. If this fails, stop and leave the files alone.
4. Perform the file actions.
5. Record the outcomes back into the report.

With the action first, the report would point at a path that no longer exists. If the report write
then failed, the data would be gone with no record of why.

## Two status axes

A single value cannot say "11 of 12 files were checked and all 11 passed", so every run carries
two:

```
run_status:    completed | partial | aborted     did Pylos do its job?
data_decision: pass | warn | fail                was the data good?
```

When one file fails, Pylos records it and carries on with the rest. A partial run on record is
better than an aborted one that leaves the day missing from the table.

## Empty runs and empty files

A run that matches no files still writes a report, so "checked, found nothing" looks different from
"Pylos never ran". Whether that counts as an error is up to the pipeline, through `on_empty`.

A file that exists but has zero rows is a separate case. An empty frame passes every column
expectation, so a day with no data would show up as a clean pass. Pylos reports it explicitly and
raises the decision from `PASS` to `WARN`.
