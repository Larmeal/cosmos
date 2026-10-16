# Pipeline

## Two verbs sharing one pipe

Pylos validates a source against a contract, and it profiles it. The two differ only in the middle
step.

```
                        ┌──── validate ────┐
Source ──[ Engine ]────►┤                  ├────► Sink
                        └──── profile ─────┘
                                 │
                (validate only)  │
                                 ▼
                          Policy ──► Action on the Source
```

Both read the source the same way, run on the same engine, and write to the same sink. Profiling
only reports and never fails, so only validation feeds the policy.

!!! note

    Validation ships first. Profiling is planned for a later release.

## Five layers

A config passes through five layers, from what the user writes to what gets recorded afterwards.

```
┌──────────────────────────────────────────────────────┐
│ 1. Declaration   YAML + Jinja                        │  what the user writes
├──────────────────────────────────────────────────────┤
│ 2. Spec          Pydantic: is it well-formed?        │  imports no engine
├──────────────────────────────────────────────────────┤
│ 3. Plan          declaration -> the list of work     │
├──────────────────────────────────────────────────────┤
│ 4. Execution     engine + GX actually run            │  pandas / spark / sql
├──────────────────────────────────────────────────────┤
│ 5. Outcome       decide -> act on source -> record   │  policy + action + sink
└──────────────────────────────────────────────────────┘
```

Layer 2 works without any engine installed. CI can check a config without Spark, and no optional
dependency is imported at module level. A dry run covers layers 1 to 3 and stops there.

Great Expectations already does nearly all of layer 4. Pylos is mostly layers 3 and 5: planning the
work, deciding what a result means, and acting on it.

## Great Expectations underneath

Pylos wraps Great Expectations and leaves its vocabulary alone. Expectation names pass through
unchanged, so `expect_column_values_to_not_be_null` in a contract is the GX expectation of the same
name.
