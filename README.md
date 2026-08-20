<p align="center">
  <img src="images\github-logo.png" width="300" height="300" />
</p>

<h1 align="center">
  <b style="font-size: 1.5em; letter-spacing: 0.15em;">✦ COSMOS ✦</b>
</h1>

<p align="center">
  <i>A framework for encapsulating Great Expectations within data pipelines</i>
</p>

<p align="center">
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.11+-blue.svg" alt="Python Version" /></a>
  <a href="https://github.com/astral-sh/ruff"><img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json" alt="Ruff" /></a>
  <a href="https://pre-commit.com/"><img src="https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit" alt="pre-commit" /></a>
  <a href="https://docs.greatexpectations.io/"><img src="https://img.shields.io/badge/great--expectations-1.x-orange.svg" alt="Great Expectations" /></a>
  <a href="https://pandas.pydata.org/"><img src="https://img.shields.io/badge/pandas-3.0-150458.svg?logo=pandas" alt="Pandas" /></a>
  <a href="https://docs.pydantic.dev/"><img src="https://img.shields.io/badge/pydantic-v2-E92063.svg?logo=pydantic" alt="Pydantic" /></a>
  <a href="https://github.com/astral-sh/uv"><img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json" alt="uv" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache%202.0-blue.svg" alt="License" /></a>
</p>

---

## What it is

**A data validation and profiling framework for data pipelines.**

COSMOS operationalizes [Great Expectations](https://greatexpectations.io/): it manages configuration,
dispatches across engines, decides what happens when validation fails, and reports results to
pluggable sinks.

It is a **layer inside** someone else's pipeline (Airflow / Dagster / a script) — not a pipeline, not
a scheduler, not an ETL tool. It is built for **automated systems that run daily and report on data
processing**, rather than for people exploring data interactively.

## What it adds over Great Expectations

| | |
|---|---|
| **Failure lifecycle** | GX reports that a batch failed; it will not move the offending file to a dead-letter location or record what happened. COSMOS does both. |
| **Multi-engine dispatch** | One declarative YAML shape running on pandas, Spark or SQL. |
| **Profiling** | GX 1.x substantially pared back the profiling story that existed in 0.x. |

## How it works

```
                        ┌──── profile ─────┐
Source ──[ Engine ]────►┤                  ├────► Sink
                        └──── validate ────┘
                                 │
                (validate only)  │
                                 ▼
                          Policy ──► Action on the Source
```

Both verbs share one pipe — same source reading, same engine, same sink. Profiling never fails, so
only validation can trigger an action on the source file.

## Features

- **One YAML file per pipeline**, parsed and validated by Pydantic. A typo fails at load, not ten
  minutes into a run.
- **Per-expectation severity** — `critical` / `warning` / `info`. Severity is what decides whether
  the pipeline acts, rather than a bare pass/fail.
- **Failure actions on the source file** — `ignore`, `move`, `copy`, `delete`, performed by the
  storage system that owns the data (GCS moves its own objects; the OS moves local files).
- **A report is always written**, independently of the file action, so "write to BigQuery *and* move
  the file" is expressible. The report is written *before* the file is touched.
- **One file = one batch**, so a result can always name the file it came from.
- **An error taxonomy that decides retryability** — `ConfigError` aborts, `DataError` dead-letters,
  and `InfraError` touches nothing so the orchestrator can retry.
- **Partial failure continues** — a bad file is skipped and recorded; the remaining files still run.
- **Library first, CLI second.** The library returns the reasoning; the CLI wraps it.

```yaml
id: customer_daily
engine: pandas

source:
  storage: local                # local | gcs
  file_format: csv
  file_path: data/*.csv
  on_empty: fail                # fail | skip

validation:
  contract:
    name: customer
    expectations:
      - expectation_type: expect_column_values_to_not_be_null
        kwargs: {column: id}
        severity: critical      # critical | warning | info

on_failure:
  action: move                  # ignore | move | copy | delete
  dead_letter: output/dead-letters/
```

## Not in scope

Scheduling · writing validated data out (ETL) · data catalog / lineage · alerting (the orchestrator's
`on_failure_callback` does it better) · exploratory data analysis · a drift platform — the
time-series table plus SQL views is the answer · an in-house expectation vocabulary, since GX
expectation names pass through unchanged.

## Roadmap

| | Ships |
|---|---|
| **v0.1** | pandas · local · validate · `action: ignore\|move` · JSON sink · library API · error taxonomy |
| **v0.2** | GCS — source and dead-letter |
| **v0.3** | BigQuery sink · `run_id` / `attempt_id` · `merge` — first production-usable version |
| **v0.4** | profiling + drift SQL views |
| **v0.5** | Jinja · contract reuse · CLI |
| **v0.6** | Spark |
| **v0.7** | SQL |

## Status

**Pre-v0.1 and under active construction.** The configuration layer, the GX adapter and local
storage work; the planner, policy, report sinks and runner are not written yet, and the config shape
is still settling. See [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md) for the full design record.

## Development

```bash
uv sync                  # install with dev groups
uv sync --extra gcp      # add the GCP extra
uv run ruff check src/   # lint
uv run pytest            # test
prek install             # pre-commit hooks
```
