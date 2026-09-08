from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from cosmos.actions import OnFailureActionConfig, RelocateFailureAction
from cosmos.engines import Engine
from cosmos.gx.models import ContractConfig, ExpectationConfig
from cosmos.results import Severity, SourceObjectMetadata
from cosmos.sinks import SinkConfig
from cosmos.sources import SourceConfig
from cosmos.storages import StorageBackend

_BOX_WIDTH = 78
_OBJECT_PREVIEW = 5
_PATH_WIDTH = 42
_SEVERITY_ORDER = (Severity.CRITICAL, Severity.WARNING, Severity.INFO)


def _elide_path(path: str) -> str:
    """Shortens a path for display by cutting from the left, not the right.

    A path's most identifying part is its end: the file name, and usually the
    parent folder or two above it. The shared prefix at the front ("the whole
    project lives under C:/Users/.../cosmos/...") tells a reader nothing new
    once they've seen it once, so that is the part that gets cut. A single
    "…" character marks that something was removed.

    Args:
        path: The path to shorten, as it would otherwise be printed.

    Returns:
        ``path`` unchanged if it already fits within ``_PATH_WIDTH``
        characters, otherwise its rightmost ``_PATH_WIDTH - 1`` characters
        prefixed with "…".

    Example:
        A 79-character absolute path becomes::

            >>> _elide_path("C:/Users/armlo/.../cosmos/data/test_1.csv")
            '…t/personal-project/cosmos/data/test_1.csv'

        while a short path like ``"data/test_1.csv"`` passes through
        untouched, since it is already under the width limit.

    Note:
        To show more or less of the path, change the module-level
        ``_PATH_WIDTH`` constant; this function itself never needs to change
        for that. It is used for both the object listing (``Plan._object_lines``)
        and nowhere else, so widening it only affects that one column.
    """
    if len(path) <= _PATH_WIDTH:
        return path
    return "…" + path[-(_PATH_WIDTH - 1) :]


def _relative_to_cwd(path: str) -> str:
    """Rewrites a local path as relative to the current directory, best-effort.

    ``LocalStorage`` resolves every object's path to an absolute one (see
    ``storages/local.py``), which is correct for identifying a file uniquely
    but painful to read in a terminal: a plan run from the project root
    should show ``data/test_1.csv``, not
    ``C:/Users/armlo/OneDrive/Desktop/Project/personal-project/cosmos/data/test_1.csv``.
    This function undoes that resolution for display purposes only; the
    ``source_object`` key COSMOS actually reports against is untouched,
    since callers pass the original ``obj.path`` to everything else.

    Args:
        path: An absolute (or otherwise non-relative) path or URI, as stored
            on ``SourceObjectMetadata.path``.

    Returns:
        ``path`` rewritten relative to :func:`pathlib.Path.cwd`, or ``path``
        unchanged when that would not help: a URI from another backend
        (``gs://bucket/key`` has no filesystem meaning to relativize), or a
        local path outside the current tree (a different drive on Windows,
        or anywhere ``Path.relative_to`` would raise).

    Example:
        Run from the project root, with the CWD at
        ``.../cosmos``::

            >>> _relative_to_cwd(".../cosmos/data/test_1.csv")
            'data/test_1.csv'
            >>> _relative_to_cwd("gs://my-bucket/data/test_1.csv")
            'gs://my-bucket/data/test_1.csv'

    Note:
        This is only ever called when ``Plan.render(full_path=False)``, the
        default; pass ``full_path=True`` to skip it and show the path exactly
        as stored. If a future storage backend needs its own notion of
        "relative", branch on a URI scheme check here rather than adding a
        second function; every call site already goes through this one.
    """
    if "://" in path:
        return path
    try:
        return str(Path(path).resolve().relative_to(Path.cwd().resolve()))
    except ValueError:
        return path


def _human_size(size_bytes: float) -> str:
    """Formats a byte count the way a person skimming a terminal reads it.

    ``SourceObjectMetadata.size_bytes`` is a plain integer, exactly the way
    ``os.stat`` reports it; nobody scanning a plan wants to mentally divide
    that by a million to tell "is this file big". This walks it up through
    B, KB, MB to GB, stopping at the first unit where the number is small
    enough to read at a glance.

    Args:
        size_bytes: A non-negative byte count, usually ``obj.size_bytes`` or
            a sum of several.

    Returns:
        The size rounded to the nearest unit: whole bytes for "B" (nobody
        needs "410.0 B"), one decimal place everywhere above that
        ("2.0 KB", "5.0 MB"), and everything at a gigabyte or larger is left
        in GB even if that means more than three digits before the point.

    Raises:
        AssertionError: Never, in practice: every branch of the loop returns
            before falling through, since "GB" always matches on its own
            check. The line exists only so a type checker can see the
            function always returns a ``str``.

    Example:
        >>> _human_size(410)
        '410 B'
        >>> _human_size(2048)
        '2.0 KB'
        >>> _human_size(5 * 1024 * 1024)
        '5.0 MB'

    Note:
        To add a "TB" tier, extend the ``for unit in (...)`` tuple; the
        division-by-1024 loop already generalizes to any number of units.
    """
    for unit in ("B", "KB", "MB", "GB"):
        if size_bytes < 1024 or unit == "GB":
            return f"{size_bytes:.0f} {unit}" if unit == "B" else f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    raise AssertionError("unreachable")


def _render_value(value: Any) -> str:
    """Renders one config value roughly the way it looked in the YAML.

    Used for values that read best as a ``key="value"`` pair rather than
    YAML's own block style, such as a source's reader ``options``
    (``delimiter=","``). Every string is quoted here, unconditionally, which
    is deliberate: this reads like a Python keyword argument, where quoting a
    string is always correct and never ambiguous. Contrast this with
    :func:`_render_kwarg_scalar`, used for the ``--full-rules`` block, which
    quotes only when leaving a string bare would change its meaning; the two
    exist side by side because they render two different notations.

    Args:
        value: A single config value: a bool, string, list, number, or
            anything whose ``str()`` is already what should be shown.

    Returns:
        ``"true"``/``"false"`` for a bool (checked before ``str``, since
        ``isinstance(True, int)`` is also true in Python and would otherwise
        print ``"1"``), a double-quoted string for ``str``, a
        ``[item, item]`` rendering for a list (each item recursed into and
        then unquoted, since a bracketed list already reads as one unit), or
        ``str(value)`` for everything else (``int``, ``float``, ``None``).

    Example:
        >>> _render_value(True)
        'true'
        >>> _render_value("utf-8")
        '"utf-8"'
        >>> _render_value(["col_int64", "col_float64"])
        '[col_int64, col_float64]'
        >>> _render_value(0)
        '0'

    Note:
        To render a new value shape (a dict, say), add a branch here before
        the final ``str(value)`` fallback; every caller in this module (the
        source options in ``Plan._source_box`` and the scalar fallback in
        ``_render_kwarg_scalar``) goes through this one function, so the
        change reaches both at once.
    """
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return f'"{value}"'
    if isinstance(value, list):
        return "[" + ", ".join(_render_value(item).strip('"') for item in value) + "]"
    return str(value)


_TIMESTAMP_LIKE = re.compile(r"^\d{4}-\d{2}-\d{2}")


def _needs_quotes(value: str) -> bool:
    """Whether writing this string bare, as plain YAML, would change its meaning.

    ``--full-rules`` renders each expectation's ``kwargs`` to look like a
    hand-written YAML file (see ``Plan._rule_lines``), and in real YAML most
    strings are written without quotes: ``column: col_int64``, not
    ``column: "col_int64"``. But a handful of strings are only strings
    because Python says so; a YAML *reader* looking at the same bare text
    would parse it as a bool, a number, or a timestamp instead. This function
    is the check for exactly those cases, so the renderer knows when it has
    to quote to keep the value a string.

    Args:
        value: The exact text that would otherwise be written bare.

    Returns:
        True when leaving ``value`` unquoted would be misread by a YAML
        parser: it is empty or has leading/trailing whitespace, it spells a
        bool or null (``"true"``, ``"None"``, ``"~"``, case-insensitively),
        it parses as a number (``float(value)`` succeeds), or it starts with
        a ``YYYY-MM-DD`` date. False for an ordinary identifier like a
        column name, which reads better, and is unambiguous, left bare.

    Example:
        >>> _needs_quotes("col_int64")
        False
        >>> _needs_quotes("2000-01-01 00:00:00")
        True
        >>> _needs_quotes("true")
        True
        >>> _needs_quotes(" col")
        True

    Note:
        This only has to cover shapes that actually appear in a GX
        expectation's ``kwargs`` today (dates, numbers-as-strings, and
        so on). If a future expectation's kwargs introduce a new ambiguous
        shape (say, a string that looks like a YAML list, ``"[1, 2]"``), add
        a check for it here; ``_render_kwarg_scalar`` is the only caller and
        needs no change itself.
    """
    if value == "" or value.strip() != value:
        return True
    if value.lower() in {"true", "false", "null", "none", "yes", "no", "~"}:
        return True
    try:
        float(value)
    except ValueError:
        pass
    else:
        return True
    return bool(_TIMESTAMP_LIKE.match(value))


def _render_kwarg_scalar(value: Any) -> str:
    """Renders one kwarg value the way a hand-written YAML file would.

    This is the ``--full-rules`` counterpart to ``_render_value``: same job,
    different notation. ``_render_value`` always quotes a string (it is
    rendering a Python-style ``key="value"`` pair); this instead quotes only
    when :func:`_needs_quotes` says leaving it bare would be misread, so a
    column name like ``col_int64`` reads the way it does in the source YAML.
    Non-string values (bools, numbers) delegate straight to ``_render_value``,
    since those never have this ambiguity.

    Args:
        value: One value from an expectation's ``kwargs`` dict, e.g. the
            ``"col_int64"`` in ``{"column": "col_int64"}``.

    Returns:
        The bare string when it is unambiguous, a double-quoted string when
        it is not, or ``_render_value(value)`` for anything that is not a
        string at all.

    Example:
        >>> _render_kwarg_scalar("col_int64")
        'col_int64'
        >>> _render_kwarg_scalar("2000-01-01 00:00:00")
        '"2000-01-01 00:00:00"'
        >>> _render_kwarg_scalar(True)
        'true'
        >>> _render_kwarg_scalar(5)
        '5'

    Note:
        Called once per non-``column_list`` value by ``_render_kwargs_lines``;
        it never needs to know about that caller's indentation or the
        ``key:`` prefix, only the value itself, which keeps it easy to reuse
        if another part of the plan ever wants the same YAML-flavored
        rendering.
    """
    if isinstance(value, str):
        return f'"{value}"' if _needs_quotes(value) else value
    return _render_value(value)


def _render_kwargs_lines(kwargs: dict[str, Any], indent: str) -> list[str]:
    """Renders one expectation's kwargs, YAML-shaped, under the given indent.

    This is the body of a single rule's ``kwargs:`` block in ``--full-rules``
    output. It walks the kwargs dict in the order it was declared (a
    ``dict`` preserves that, and so does PyYAML's loader), and renders each
    key on its own line, the same "key: value" shape the source YAML used.
    ``column_list`` is the one exception: since
    ``expect_table_columns_to_match_ordered_list`` is about the columns'
    *order*, that list explodes into one bare item per line rather than the
    single-line ``[a, b, c]`` every other list would get, so the order is
    something a reader can actually see rather than infer from a bracket.

    Args:
        kwargs: One expectation's ``kwargs`` dict, e.g.
            ``{"column": "col_int64", "min_value": 0, "max_value": 5}``.
        indent: The literal whitespace prefix for every line this returns,
            already computed by the caller to line up under that rule's
            number (see ``Plan._rule_lines``).

    Returns:
        One line per key, each already prefixed with ``indent``, ready to be
        extended straight onto the growing list of plan lines. A
        ``column_list`` key contributes a ``"column_list:"`` line plus one
        ``"  - <name>"`` line per column, indented two further spaces.

    Example:
        >>> _render_kwargs_lines(
        ...     {"column": "col_int64", "min_value": 0, "max_value": 5},
        ...     indent="          ",
        ... )
        ['          column: col_int64', '          min_value: 0', '          max_value: 5']

    Note:
        The ``column_list`` special case is hardcoded by key name rather than
        by shape (e.g. "any list longer than N items"), because it is the
        only GX kwarg where order is the point of the expectation; every
        other list-valued kwarg (``value_set``, say) is unordered and reads
        fine as ``_render_value``'s ``[true, false]``. If a future
        expectation needs the same one-per-line treatment, add its key
        alongside ``"column_list"`` in the condition below rather than
        switching to a general "explode all lists" rule.
    """
    lines: list[str] = []
    for key, value in kwargs.items():
        if key == "column_list" and isinstance(value, list):
            lines.append(f"{indent}{key}:")
            lines.extend(f"{indent}  - {item}" for item in value)
        else:
            lines.append(f"{indent}{key}: {_render_kwarg_scalar(value)}")
    return lines


def _box(title: str, rows: list[tuple[str, str]]) -> list[str]:
    """Draws one titled box, every box the same width so they stack cleanly.

    This is the one drawing routine every section of the plan goes through
    (``source``, ``validate``, ``on failure``, ``report``); nothing else in
    the file builds a box border by hand. A "row" is a ``(label, value)``
    pair. Two things are worth knowing about how it lays them out:

    1. Every row's colon lines up under the *box's* longest label (not the
       whole plan's), one space after it, so ``storage``, ``reader`` and
       ``options`` in the source box all get their ``:`` at the same column
       even though the labels are different lengths.
    2. A row whose label is ``""`` is a *continuation* of the row above it,
       used when one logical value spans several lines (a wrapped list of
       reader options, or the per-severity rule counts). It gets no label or
       colon of its own, just enough leading whitespace to land under where
       the first line's value began, so the whole block reads as one item.

    Args:
        title: The box's name, shown in its top border (``"╭─ source ─..."``).
        rows: The box's content, top to bottom. At least one row must have a
            non-empty label, since that is what fixes the column the colons
            align to.

    Returns:
        The box as a list of already-bordered, already-padded lines: a top
        border, one line per row, and a bottom border. Every line is exactly
        ``_BOX_WIDTH`` characters, so boxes stack without a ragged right edge.

    Example:
        >>> for line in _box("on failure", [("action", "move"), ("dead letter", "output/dead-letters")]):
        ...     print(line)
        ╭─ on failure ───────────────────────────────────────────────────────────────╮
        │  action      : move                                                        │
        │  dead letter : output/dead-letters                                         │
        ╰────────────────────────────────────────────────────────────────────────────╯

    Note:
        To change the box's total width, edit the module-level ``_BOX_WIDTH``
        constant, not this function. To change the alignment rule itself
        (say, left-aligning values instead of aligning colons), this is the
        only function that needs to change; every ``Plan._*_box`` method
        just builds ``rows`` and hands them here.
    """
    head = f"╭─ {title} "
    lines = [head + "─" * (_BOX_WIDTH - len(head) - 1) + "╮"]

    label_width = max(len(label) for label, _ in rows if label)
    for label, value in rows:
        if label:
            body = f"  {label.ljust(label_width + 1)}: {value}"
        else:
            body = " " * (label_width + 5) + value
        lines.append("│" + body.ljust(_BOX_WIDTH - 2) + "│")

    lines.append("╰" + "─" * (_BOX_WIDTH - 2) + "╯")
    return lines


@dataclass
class Plan:
    """What the run will do, resolved against reality but with nothing executed.

    Config alone cannot answer "which files will this touch", and the file list
    alone cannot answer "what will happen to them". Plan is the two together,
    which is what makes it worth rendering before a run rather than after.

    A ``Plan`` is a plain ``@dataclass``, not a Pydantic model, even though
    every field it holds (``source``, ``contract``, ...) is itself a
    validated Pydantic model. That is deliberate: those sub-models already
    ran their validators once, when the engine's YAML was loaded, and a
    dataclass never re-runs them, whereas nesting an already-validated model
    inside another ``BaseModel`` can re-trigger its ``model_validator``\\ s
    unexpectedly. ``Plan`` only ever reads its fields; it is a snapshot, not
    something a caller is expected to construct by hand except in a test.

    Attributes:
        engine_id: The pipeline's stable ``id``, shown in the header.
        engine_name: Which engine will read the data ("pandas", "spark", "sql").
        source: The declared source, for the pattern, reader and options.
        contract: The rules that will be applied to every object.
        on_failure: What happens to an object whose critical rules fail.
        report: Where the report is written, whatever the outcome.
        data_docs_enabled: Whether GX will also render its HTML view.
        source_objects: What the glob actually found, sorted by path.

    Example:
        Ordinarily built by ``Planner.plan()``, never by hand, but nothing
        stops a test from constructing one directly with fabricated data,
        which is how this file's own edge cases (an empty glob, 30 objects
        needing truncation) get exercised without touching a real filesystem::

            >>> plan = Plan(
            ...     engine_id="test_config",
            ...     engine_name="pandas",
            ...     source=source_config,
            ...     contract=contract_config,
            ...     on_failure=IgnoreFailureAction(),
            ...     report=report_config,
            ...     data_docs_enabled=False,
            ...     source_objects=[],
            ... )
            >>> print(plan.render())
    """

    engine_id: str
    engine_name: str
    source: SourceConfig
    contract: ContractConfig
    on_failure: OnFailureActionConfig
    report: SinkConfig
    data_docs_enabled: bool
    source_objects: list[SourceObjectMetadata]

    def ordered_expectations(self) -> list[ExpectationConfig]:
        """Every rule, severity first and declaration order within each severity.

        This is the single source of truth for "what order do the rules
        appear in", used by both ``_rule_lines`` (numbering ``--full-rules``)
        and eventually anywhere else that needs to say "rule 4" and mean the
        same rule every time (a report, a log line). It is a public method,
        not a leading-underscore helper, precisely so those other callers can
        reuse it instead of re-deriving the same order by hand.

        Both keys the ordering depends on (a rule's ``severity``, and its
        position in ``self.contract.expectations``) come from the config
        alone, never from anything resolved at plan time. That is what makes
        the order deterministic: running the same contract through this
        twice, or on two different machines, always numbers the rules
        identically.

        Returns:
            Every expectation in ``self.contract.expectations``, grouped by
            severity in the order ``critical``, ``warning``, ``info``
            (``_SEVERITY_ORDER``), and in declaration order within each
            group. The list is a new one; the contract's own list is left
            untouched.

        Example:
            A contract declaring ``[warning_rule, critical_rule]`` (in that
            order) returns ``[critical_rule, warning_rule]``: severity always
            wins over declaration order, even though ``critical_rule`` was
            written second.

        Note:
            To change the severity ordering itself (say, ``info`` before
            ``warning``), edit the module-level ``_SEVERITY_ORDER`` tuple;
            this method and everything that calls it adapts automatically,
            since none of them hardcode the three names.
        """
        ordered: list[ExpectationConfig] = []
        for severity in _SEVERITY_ORDER:
            ordered.extend(rule for rule in self.contract.expectations if rule.severity == severity)
        return ordered

    def _source_box(self) -> list[str]:
        """Builds the ``╭─ source ─...`` box: where the data comes from.

        Assembles the rows for storage, reader, options and glob pattern into
        the shape ``_box`` expects, then hands them off; this method owns no
        drawing logic of its own; it turns ``self.source`` (a ``SourceConfig``)
        into ``(label, value)`` pairs.

        Returns:
            The finished, bordered box as a list of lines (see ``_box``).
            Each reader option becomes its own row (``options`` on the first,
            an empty label continuing it on the rest), so
            ``{"delimiter": ",", "encoding": "utf-8"}`` renders as two lines,
            one option each, not packed onto one.

        Example:
            For a CSV source with two options and a wildcard pattern, this
            returns a box whose rows read (label, value) as::

                ("storage", "local")
                ("reader", "pandas.read_csv")
                ("options", 'delimiter=","')
                ("", 'encoding="utf-8"')
                ("pattern", "data/test_*.csv")
                ("on_empty", "skip")

        Note:
            To show a new source field (say, a future ``compression``
            option), add a row to the ``rows`` list here; ``_box`` handles
            the alignment for whatever rows it is given, with no changes
            needed there.
        """
        rows = [
            ("storage", self.source.storage),
            ("reader", f"{self.engine_name}.read_{self.source.file_format}"),
        ]
        option_lines = [f"{key}={_render_value(value)}" for key, value in self.source.options.items()]
        for index, line in enumerate(option_lines):
            rows.append(("options" if index == 0 else "", line))
        rows.append(("pattern", self.source.file_path))
        rows.append(("on_empty", self.source.on_empty))
        return _box("source", rows)

    def _object_lines(self, full: bool, full_path: bool, tz: ZoneInfo) -> list[str]:
        """Lists the resolved source objects: what the glob actually found.

        This is the one part of the plan that reports on reality rather than
        declaration: ``self.source_objects`` came from an actual
        ``backend.glob()`` call (see ``Planner.prepare_source_metadata``), so
        this can say "12 objects, 5.1 KB" instead of "however many files
        happen to match, whenever the run actually starts". It sits outside
        any ``╭─...╮`` box on purpose (compare ``_source_box``): a list of an
        arbitrary, possibly large number of files does not fit the
        fixed-width row format the boxes use.

        Args:
            full: List every object instead of only the first
                ``_OBJECT_PREVIEW`` (5), with a leading index number on each
                line. Corresponds to the CLI's future ``--full-objects``.
            full_path: Show each object's path exactly as stored (absolute,
                for local files) instead of relative to the current
                directory. See ``_relative_to_cwd``.
            tz: The zone to render each object's ``modified`` timestamp in,
                already resolved by ``render()`` from its ``timezone``
                argument.

        Returns:
            Lines to insert into the plan, starting with a blank line and a
            summary ("N objects resolved · size"), followed by one line per
            listed object, and (when ``full`` is False and there are more
            than ``_OBJECT_PREVIEW``) a final "… N more" line. Returns just
            a "0 objects resolved" line, with no summary or listing, when the
            glob matched nothing.

        Example:
            With ``full=False`` and three objects found::

                    3 objects resolved · 1.2 KB

                      data/test_1.csv                410 B   modified 2026-09-08 21:25
                      data/test_2.csv                533 B   modified 2026-08-28 00:07
                      data/test_3.csv                410 B   modified 2026-05-23 15:28

        Note:
            The preview size is the module-level ``_OBJECT_PREVIEW``
            constant, and each path's column width is ``_PATH_WIDTH``
            (via ``_elide_path``); adjust those rather than the layout
            arithmetic in this method.
        """
        total = len(self.source_objects)
        total_size = sum(obj.size_bytes for obj in self.source_objects)

        noun = "object" if total == 1 else "objects"
        if not total:
            return ["", f"    0 {noun} resolved"]

        lines = ["", f"    {total:,} {noun} resolved · {_human_size(total_size)}", ""]

        shown = self.source_objects if full else self.source_objects[:_OBJECT_PREVIEW]
        for index, obj in enumerate(shown, start=1):
            size = _human_size(obj.size_bytes).rjust(8)
            stamp = obj.modified.astimezone(tz).strftime("%Y-%m-%d %H:%M")
            display_path = obj.path if full_path else _relative_to_cwd(obj.path)
            prefix = f"{index:>8}  " if full else "      "
            lines.append(f"{prefix}{_elide_path(display_path).ljust(30)}{size}   modified {stamp}")

        if not full and total > _OBJECT_PREVIEW:
            lines.append(f"      … {total - _OBJECT_PREVIEW:,} more")
        return lines

    def _validate_box(self) -> list[str]:
        """Builds the ``╭─ validate ─...`` box: the contract, in summary.

        Shows counts only (a "9 totals / 8 critical / 1 warning" breakdown),
        never the rules themselves; that is deliberately left to
        ``_rule_lines`` (only shown when ``--full-rules`` is passed), since
        the counts fit in a fixed-height box and a rule list does not. The
        per-severity rows are built the same "continuation row" way as
        ``_source_box``'s options: a first row with the ``rules`` label, then
        one unlabeled row per severity that has at least one rule, so
        ``_box`` lines the counts up under "N totals" automatically.

        Returns:
            The finished, bordered box (see ``_box``). A severity with zero
            rules gets no row at all: a contract with only critical rules
            shows no "0 warning" line.

        Example:
            For a contract with 8 critical and 1 warning rule, the rows
            (label, value) read::

                ("contract", "test_1_schema")
                ("rules", "9 totals")
                ("", "8 critical")
                ("", "1 warning")
                ("data docs", "disabled")

        Note:
            The severities iterated here come from the module-level
            ``_SEVERITY_ORDER``, same as everywhere else in the file; adding
            a fourth severity there is the only change needed for it to show
            up here too.
        """
        total = len(self.contract.expectations)
        noun = "total" if total == 1 else "totals"

        rows = [
            ("contract", self.contract.data_asset_name),
            ("rules", f"{total} {noun}"),
        ]
        for severity in _SEVERITY_ORDER:
            count = sum(1 for rule in self.contract.expectations if rule.severity == severity)
            if count:
                rows.append(("", f"{count} {severity}"))
        rows.append(("data docs", "enabled" if self.data_docs_enabled else "disabled"))
        return _box("validate", rows)

    def _rule_lines(self) -> list[str]:
        """Every rule, numbered and grouped by severity, kwargs shown YAML-style.

        Only called when ``render(full_rules=True)``; the default plan shows
        just ``_validate_box``'s counts, since 12 multi-line rule blocks is a
        lot to put in front of someone who only wants to know "does this
        plan look right". Each rule renders like an entry from the original
        contract YAML (``expectation_type:`` then an indented ``kwargs:``
        block, via ``_render_kwargs_lines``), except the ``-`` a plain YAML
        list would use is replaced by the rule's number. That makes a rule
        addressable the same way whether you are reading the plan or a
        report ("rule 4 failed" means the same rule in both), which plain
        ``-`` bullets, or names alone (not every rule has one), cannot do.

        Returns:
            Lines to insert into the plan: for each severity that has at
            least one rule, a blank line, a "<severity> · N rules" header,
            then each rule as a blank line, its numbered
            ``expectation_type:`` line, and (if it has any) an indented
            ``kwargs:`` block. Returns an empty list if the contract has no
            expectations at all.

        Example:
            A single ``expect_column_values_to_not_be_null`` critical rule
            on ``col_int64`` renders as::

                    critical · 1 rule

                       1  expectation_type: expect_column_values_to_not_be_null
                          kwargs:
                            column: col_int64

        Note:
            Numbering restarts at 1 and counts up across every severity
            group in one pass (it does not reset per group), which is why
            ``number`` is declared once, outside the ``for severity`` loop,
            and only ever incremented, never reset.
        """
        ordered = self.ordered_expectations()
        if not ordered:
            return []

        lines: list[str] = []
        number = 0
        for severity in _SEVERITY_ORDER:
            group = [rule for rule in ordered if rule.severity == severity]
            if not group:
                continue
            noun = "rule" if len(group) == 1 else "rules"
            lines.extend(["", f"    {severity} · {len(group)} {noun}"])
            for rule in group:
                number += 1
                prefix = f"{number:>8}  "
                indent = " " * len(prefix)
                lines.append("")
                lines.append(f"{prefix}expectation_type: {rule.expectation_type}")
                if rule.kwargs:
                    lines.append(f"{indent}kwargs:")
                    lines.extend(_render_kwargs_lines(rule.kwargs, indent + "  "))
        return lines

    def _on_failure_box(self) -> list[str]:
        """Builds the ``╭─ on failure ─...`` box: what happens to a bad file.

        ``self.on_failure`` is a discriminated union (``IgnoreFailureAction``,
        ``DeleteFailureAction``, ``RelocateFailureAction``, ...), and only
        ``RelocateFailureAction`` (COSMOS's ``move``/``copy``) has a
        destination worth showing; every other action's ``action`` field
        alone already says everything there is to say. That is why this is
        an ``isinstance`` check rather than a fixed set of rows: the box has
        one row for ``action: ignore`` or ``action: delete``, and two for
        ``action: move``, without ``_box`` needing to know why.

        Returns:
            The finished, bordered box (see ``_box``): always an ``action``
            row, plus a ``dead letter`` row only when ``self.on_failure`` is
            a ``RelocateFailureAction``.

        Example:
            For ``on_failure: {action: move, dead_letter: output/dead-letters/}``,
            the rows read ``[("action", "move"), ("dead letter", "output/dead-letters/")]``;
            for ``action: ignore``, just ``[("action", "ignore")]``.

        Note:
            A future action that also needs an extra row (say, ``copy``
            wanting to show whether it overwrites) follows the same pattern:
            add an ``isinstance`` branch here, not a change to ``_box``.
        """
        rows: list[tuple[str, str]] = [("action", self.on_failure.action)]
        if isinstance(self.on_failure, RelocateFailureAction):
            rows.append(("dead letter", self.on_failure.dead_letter))
        return _box("on failure", rows)

    def _report_box(self) -> list[str]:
        """Builds the ``╭─ report ─...`` box: where the results are written.

        Short by design: a report is always written, pass or fail (per the
        project's failure-handling rules), so unlike ``on failure`` there is
        no conditional content here, just where it lands and how many rows
        it will have (one per expectation per object; the object count is
        deliberately left out of the box itself, since it can be large and
        already has its own summary line in ``_object_lines``).

        Returns:
            The finished, bordered box (see ``_box``), with a ``save on``
            row (the sink's ``path`` if it has one, otherwise its
            ``storage``) and an ``expectations`` row.

        Example:
            For a local file sink at ``output/reports/`` and a 9-rule
            contract, the rows read
            ``[("save on", "output/reports/"), ("expectations", "9")]``.

        Note:
            ``getattr(self.report, "path", None)`` exists because not every
            ``SinkConfig`` has a ``path`` (a BigQuery sink, say, would not);
            falling back to ``self.report.storage`` keeps this box working
            for any sink type without an ``isinstance`` check per type.
        """
        destination = getattr(self.report, "path", None) or self.report.storage
        rows = [
            ("save on", destination),
            ("expectations", str(len(self.contract.expectations))),
        ]
        return _box("report", rows)

    def render(
        self,
        full_objects: bool = False,
        full_rules: bool = False,
        full_path: bool = False,
        timezone: str = "UTC",
    ) -> str:
        """Renders the plan for a terminal: the one public entry point of this file.

        Everything else in ``Plan`` and the module-level helpers exist to
        support this method; a caller (today a script, later a CLI's
        ``--dry`` command) only ever needs ``Planner(engine).plan().render()``.
        It assembles the five boxes and the object listing in a fixed order
        (source, objects, validate, rules, on failure, report, summary), and
        every argument controls verbosity only: none of them change what the
        run would actually do, only how much of it this particular call
        chooses to print.

        Args:
            full_objects: List every resolved object instead of the first
                five (see ``_object_lines``). Meant for a CLI's future
                ``--full-objects`` flag.
            full_rules: List every rule, not just the per-severity counts
                (see ``_rule_lines``). Meant for a CLI's future
                ``--full-rules`` flag.
            full_path: Show each object's path exactly as stored instead of
                relative to the current directory (see ``_relative_to_cwd``).
                Meant for a CLI's future ``--full-path`` flag.
            timezone: IANA zone name to render each object's modified time
                in, e.g. ``"Asia/Bangkok"``. A viewer's preference, not part
                of the plan itself, which is why it is a render argument
                rather than a ``Plan`` field: the same ``Plan`` renders in
                whatever zone whoever is reading it asks for, without
                needing to be rebuilt.

        Returns:
            The complete plan as one multi-line string, ready to ``print()``.
            Every line is padded or bordered to a consistent width (see
            ``_BOX_WIDTH``), so it looks correct in a monospace terminal.

        Raises:
            ValueError: ``timezone`` is not a recognized IANA zone name (for
                example, a typo like ``"Asia/Bangkog"``). Raised here, at the
                start of the call, before any line is built, so a bad
                timezone never produces a half-rendered plan.

        Example:
            >>> print(Planner(engine).plan().render())
              COSMOS plan · test_config · pandas
            <BLANKLINE>
            ╭─ source ───────────────────────────────────────────────────────────────────╮
            │  storage  : local                                                          │
            ...
              Plan: 1 object · 9 expectations

        Note:
            To add a new section to the plan (say, a future ``runtime`` box
            once checkpointing exists), write a ``Plan._runtime_box`` method
            following the pattern of the others and call it here, at the
            point in the sequence where it belongs; nothing about the
            existing boxes needs to change to make room for it.
        """
        try:
            tz = ZoneInfo(timezone)
        except ZoneInfoNotFoundError as exc:
            raise ValueError(f"Unknown IANA timezone {timezone!r}.") from exc

        total = len(self.source_objects)
        noun = "object" if total == 1 else "objects"

        lines = ["", f"  COSMOS plan · {self.engine_id} · {self.engine_name}", ""]
        lines.extend(self._source_box())
        lines.extend(self._object_lines(full=full_objects, full_path=full_path, tz=tz))
        lines.append("")
        lines.extend(self._validate_box())
        if full_rules:
            lines.extend(self._rule_lines())
        lines.append("")
        lines.extend(self._on_failure_box())
        lines.append("")
        lines.extend(self._report_box())
        lines.extend(["", f"  Plan: {total:,} {noun} · {len(self.contract.expectations)} expectations", ""])
        return "\n".join(lines)


class Planner:
    """Turns a declaration into the concrete work a run would do.

    The one place a glob is resolved, and the only part of a dry run that
    touches the outside world. Listing is all it does: no file is opened, no
    expectation is run, nothing is moved and nothing is written, so there is no
    effectful path here to switch off when the run is a dry one.

    ``Planner`` (this class, does the I/O) and ``Plan`` (the dataclass above,
    pure formatting) are deliberately two classes rather than one: it is what
    lets ``Plan.render()`` be tested with fabricated data and no real
    filesystem, and what lets the same resolved ``Plan`` be rendered several
    times (different ``timezone``, ``full_rules``, ...) without re-globbing.

    Example:
        >>> from cosmos.loader import from_yaml
        >>> engine = from_yaml("data/template_test.yml")
        >>> print(Planner(engine).plan().render())
          COSMOS plan · test_config · pandas
        ...
    """

    def __init__(self, engine: Engine) -> None:
        """Builds a ``Planner`` for one engine's declaration.

        Args:
            engine: The already-loaded, already-validated pipeline
                declaration (typically ``cosmos.loader.from_yaml(...)``'s
                result). Nothing here re-reads or re-validates it; ``Planner``
                assumes it is a finished ``Engine``, not a place to catch
                config mistakes (that already happened at load time).

        Note:
            ``self.backend`` is pulled out once, here, purely as a
            convenience so ``prepare_source_metadata`` reads as
            ``self.backend.glob(...)`` instead of
            ``self.engine.source.backend.glob(...)``; it is still the exact
            same object as ``engine.source.backend``, not a copy.
        """
        self.engine = engine
        self.source_config = self.engine.source
        self.validation_config = self.engine.validation
        self.backend: StorageBackend = self.source_config.backend

    def prepare_source_metadata(self) -> list[SourceObjectMetadata]:
        """Resolves the source's glob pattern against reality, right now.

        This is the one line in the whole module that does I/O: everything
        else in ``planner.py`` only formats data that was already fetched.
        Calling this twice can return two different answers (a file could
        appear or disappear between calls), which is exactly why ``Plan`` is
        a frozen snapshot: ``Planner.plan()`` calls this once and the
        resulting list is what every part of ``render()`` reports against,
        so the numbers in one printed plan are always internally consistent
        even if the filesystem keeps changing underneath it.

        Returns:
            Every object the source's glob pattern matched, as
            ``SourceObjectMetadata`` (path, size, modified time), sorted by
            path. Sorting makes the "first five" preview in
            ``Plan._object_lines`` and the full listing deterministic
            between runs, rather than however the backend happened to list
            them.

        Example:
            For ``source.file_path: "data/test_*.csv"`` matching three
            files, this returns a three-item list, sorted
            ``test_1.csv, test_2.csv, test_3.csv``, each with its own
            ``size_bytes`` and ``modified`` timestamp from the filesystem.

        Note:
            The actual listing logic (what "glob" means for local files vs.
            a GCS bucket) lives in the storage backend
            (``self.backend.glob``, e.g. ``storages/local.py``), not here;
            this method only calls it and sorts the result, so it works
            unchanged for every backend that implements ``StorageBackend``.
        """
        return sorted(self.backend.glob(pattern=self.source_config.file_path), key=lambda x: x.path)

    def plan(self) -> Plan:
        """Resolves the declaration into a ``Plan``: the module's main entry point.

        This is the method other code (a future CLI, a test, this file's own
        examples) is expected to call; everything else on ``Planner`` and
        ``Plan`` exists to support it. It does exactly two things: resolve
        the source's glob against the real filesystem
        (``prepare_source_metadata``), and copy every other field straight
        off ``self.engine`` unchanged, since those are declared, not
        discovered, and need no resolving at all.

        Returns:
            A ``Plan`` combining ``self.engine``'s declaration with
            ``prepare_source_metadata()``'s result. Call ``.render()`` on it
            to get the printable plan.

        Example:
            >>> plan = Planner(engine).plan()
            >>> plan.engine_id
            'test_config'
            >>> len(plan.source_objects)
            1

        Note:
            To resolve something else at plan time (say, checking the report
            sink's directory is writable), add it here as another field
            passed to ``Plan(...)``, following the same pattern as
            ``source_objects``: do the resolving in ``Planner.plan()``, keep
            ``Plan`` itself a plain snapshot of the result.
        """
        return Plan(
            engine_id=self.engine.id,
            engine_name=self.engine.engine,
            source=self.source_config,
            contract=self.validation_config.contract,
            on_failure=self.engine.on_failure,
            report=self.engine.report,
            data_docs_enabled=self.validation_config.data_docs.enabled,
            source_objects=self.prepare_source_metadata(),
        )
