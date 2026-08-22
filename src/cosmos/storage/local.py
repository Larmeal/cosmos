from __future__ import annotations

import logging
import shutil
from glob import glob as _fs_glob
from pathlib import Path
from typing import Literal

from pydantic import Field

from cosmos.storage.base import BaseStorage

logger = logging.getLogger(__name__)


class LocalStorage(BaseStorage):
    """Files on the machine COSMOS runs on. The OS performs every operation.

    Knows nothing about failure actions: it is handed a source and a destination
    and moves bytes. Which file to move, where to, and what the outcome means are
    decided in ``actions.py``.
    """

    storage: Literal["local"] = Field(description="The storage backend type, such as 'local'")

    @staticmethod
    def _prepare(src: str, dst_dir: str) -> Path:
        """Create the destination directory and work out the target path.

        The moved file keeps its own name, so two origins sharing a basename
        resolve to the same target. See ``move`` for what that costs.

        Args:
            src: Path of the file about to be relocated.
            dst_dir: Directory to relocate it into. Created, parents included,
                if it does not already exist.

        Returns:
            The full destination path, which does not exist yet.

        Raises:
            OSError: If the directory cannot be created — most often
                ``PermissionError``, or ``NotADirectoryError`` when a file
                already occupies the path.
        """
        directory = Path(dst_dir)
        directory.mkdir(parents=True, exist_ok=True)
        return directory / Path(src).name

    def glob(self, pattern: str) -> list[str]:
        """Expand a local glob into the files it matches.

        Relative and absolute patterns are both accepted, as is a recursive
        ``**``. Directories are filtered out, so a pattern that matches one
        contributes nothing rather than producing an origin that cannot be read.

        Args:
            pattern: A local glob, e.g. ``data/test_*.csv``. A path with no
                wildcard matches only itself.

        Returns:
            The matching file paths, sorted, so the order a run processes its
            origins in is reproducible. Empty when nothing matches, which is a
            valid outcome that ``source.on_empty`` assigns meaning to.
        """
        return sorted(p for p in _fs_glob(pattern, recursive=True) if Path(p).is_file())

    def move_obj(self, src: str, dst_dir: str) -> str:
        """Move a file into a directory, letting the OS perform the move.

        Within one filesystem this is a rename and therefore atomic; across
        devices ``shutil`` degrades to copy-then-delete, which can leave the file
        in both places if the delete fails.

        Note:
            The destination keeps the source's file name, so moving
            ``2026-08-15/orders.csv`` and ``2026-08-16/orders.csv`` into the same
            directory leaves only the second — silently, on both Windows and
            POSIX. Callers that dead-letter files from more than one directory
            should pass a distinct ``dst_dir`` per run.

        Args:
            src: Path of the file to move.
            dst_dir: Directory to move it into. Created if absent.

        Returns:
            The full path of the moved file, for the report to record beside the
            original.

        Raises:
            OSError: If the source cannot be read or the destination written.
        """
        dest = self._prepare(src, dst_dir)
        shutil.move(src, dest)
        logger.info("moved %s -> %s", src, dest)
        return str(dest)

    def copy_obj(self, src: str, dst_dir: str) -> str:
        """Copy a file into a directory, leaving the original in place.

        Metadata is preserved (``shutil.copy2``), so the copy keeps the
        modification time the pipeline may have selected the file by.

        Note:
            Overwrites an existing file of the same name, exactly as ``move``
            does.

        Args:
            src: Path of the file to copy.
            dst_dir: Directory to copy it into. Created if absent.

        Returns:
            The full path of the copy.

        Raises:
            OSError: If the source cannot be read or the destination written.
        """
        dest = self._prepare(src, dst_dir)
        shutil.copy2(src, dest)
        logger.info("copied %s -> %s", src, dest)
        return str(dest)

    def delete_obj(self, uri: str) -> None:
        """Delete a file, treating one that is already gone as success.

        A re-run after a crash mid-action can find the file deleted by the
        previous attempt. Raising there would abort a run over something already
        in the state it was asked to reach, so absence is logged and accepted —
        the report is what records whether the first attempt got this far.

        Args:
            uri: Path of the file to delete.

        Raises:
            OSError: If the file exists but cannot be removed, such as
                ``PermissionError`` when another process holds it open.
        """
        path = Path(uri)
        if not path.exists():
            logger.warning("nothing to delete at %s; it may already be gone", uri)
            return
        path.unlink()
        logger.info("deleted %s", uri)
