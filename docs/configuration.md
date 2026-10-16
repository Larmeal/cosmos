# Configuration

!!! note "Work in progress"

    The configuration models are still being renamed and reshaped, so a hand-written reference
    would go stale quickly. Until they settle, the [API Reference](reference/index.md) is the
    source of truth: every config class is documented there with its fields and defaults.

A Pylos config is a YAML file with these top-level keys:

| Key | What it holds |
|---|---|
| `id` | The name of the dataset. Part of the identity of every report row. |
| `engine` | `pandas` today. Spark and SQL are planned. |
| `source` | Where the data lives and how to read it. |
| `validate` | The contract (expectations and their severities) and `on_failure`. |
| `report` | The sinks that receive the results. |

For a complete example, see [Getting started](getting-started.md).
