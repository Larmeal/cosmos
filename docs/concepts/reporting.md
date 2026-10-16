# Reporting

Every run writes a report. Pylos is meant to run unattended every day, so the report is what the
next person or machine reads.

## Sinks

A sink receives reports. One `Sink` abstraction serves both validation and profile reports, and
each sink serializes for itself: the file sink writes a JSON document, and a BigQuery sink
flattens the report to rows.

The first release ships the JSON file sink. BigQuery follows in a later release.

## Identity and retries

Orchestrators retry, so a rerun must not duplicate rows. Two identifiers handle this, the same
split Airflow makes between `run_id` and `try_number`:

| | Derived from | Used for |
|---|---|---|
| `run_id` | `id` plus the caller's `run_key`, deterministic | De-duplication and grouping history |
| `attempt_id` | Unique per process | Telling which attempt wrote a row |

`run_key` is the time dimension the caller supplies (Airflow passes `data_interval_start`). Rerun
with the same `run_key` and you get the same `run_id`, so rows merge onto themselves. If
idempotency is on and `run_key` is missing, the config fails to load. Guessing a default could
break de-duplication silently.

A row is identified by `run_id`, the full URI of the source object, and an expectation key. The
expectation key has to cover the kwargs as well as the type, since `not_null` can appear on four
columns in one contract.

## Written twice, so merged

Each source object's row is written before the file action, with `action_result = PENDING`, and
written again once the outcome is known. Sinks therefore merge on row identity instead of
appending. Appending would leave two contradictory rows.

A row still at `PENDING` means Pylos was about to act and never recorded whether it did. A file
move and a database write cannot be made atomic, so this window cannot be closed. It can be
detected, though, by a query for rows stuck at `PENDING` past some age.

Two rules protect that evidence:

- A merge never deletes rows it did not match. After a crash during a move, the rerun sees one
  file fewer, and deleting unmatched rows would erase the only record that it failed.
- An overwrite never reaches beyond the scope being written. A table-wide overwrite would destroy
  all history.

## Run-level verdicts come last

`run_status` and `data_decision` are rollups over every object, so they are unknown while the loop
is still running. Rows are written with them empty, and a final merge on `run_id` fills them in.
Rows that still have them empty after a long time belong to a run that started and never
finished, and they show how far it got.
