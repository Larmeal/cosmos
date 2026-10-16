"""Generate the API reference pages and their navigation.

Runs inside the ``gen-files`` plugin on every build. It walks ``src/pylos`` and writes one
page per module under ``reference/``, each holding a single ``:::`` directive that
mkdocstrings expands. The navigation goes to ``reference/SUMMARY.md``, which
``literate-nav`` reads, so a new module appears in the docs without touching any config.
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import mkdocs_gen_files

PACKAGE = "pylos"

# Directories left out of the reference because they are internal plumbing, not API.
EXCLUDED_DIRS: tuple[str, ...] = ("utils",)

ROOT = Path(__file__).parent.parent
SRC = ROOT / "src" / PACKAGE

MODULE_SYMBOL = '<code class="doc-symbol doc-symbol-nav doc-symbol-module"></code>'

nav = mkdocs_gen_files.Nav()

for path in sorted(SRC.rglob("*.py")):
    relative = path.relative_to(SRC)

    if any(part in EXCLUDED_DIRS for part in relative.parts):
        continue

    # A module that has not been written yet would render as an empty page.
    if not path.read_text(encoding="utf-8").strip():
        continue

    parts = tuple(relative.with_suffix("").parts)
    doc_path = relative.with_suffix(".md")

    if parts[-1] == "__init__":
        parts = parts[:-1]
        doc_path = doc_path.with_name("index.md")
    elif parts[-1].startswith("_"):
        continue

    # The top-level ``pylos/__init__.py`` has no name to show beneath the package.
    if not parts:
        continue

    nav[tuple(f"{MODULE_SYMBOL} {part}" for part in parts)] = doc_path.as_posix()

    full_doc_path = Path("reference", doc_path)
    identifier = ".".join((PACKAGE, *parts))

    with mkdocs_gen_files.open(full_doc_path, "w") as fd:
        fd.write(
            dedent(
                f"""\
                ---
                title: {parts[-1]}
                ---

                ::: {identifier}
                    options:
                      heading_level: 2
                """
            )
        )

    # edit_uri points into docs/, so the source file is reached from one level up.
    mkdocs_gen_files.set_edit_path(full_doc_path, "../" + path.relative_to(ROOT).as_posix())

with mkdocs_gen_files.open("reference/SUMMARY.md", "w") as nav_file:
    nav_file.writelines(nav.build_literate_nav())
