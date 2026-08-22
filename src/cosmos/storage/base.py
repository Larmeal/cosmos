from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel


class BaseStorage(BaseModel, ABC):
    """Interface for file operations on a storage backend.

    One subclass per backend — local disk, GCS, S3 — each implemented with that
    backend's own SDK. ``glob`` resolves a source pattern into the files a run
    will process; ``move``, ``copy`` and ``delete`` relocate or remove a file
    after validation fails.

    Reading is not part of this interface: engines read by URI with their own
    readers.

    Paths are URIs in whatever form the backend uses — filesystem paths for local
    storage, ``gs://bucket/key`` for GCS.
    """

    @abstractmethod
    def glob(self, pattern: str) -> list[str]:
        """Expand a pattern into the URIs of the files it matches.

        Args:
            pattern: A glob in the backend's syntax, such as ``data/test_*.csv``.
                A pattern containing no wildcard matches only itself.

        Returns:
            The matching file URIs, sorted. Directories are excluded. Empty when
            nothing matches.
        """

    @abstractmethod
    def move_obj(self, src: str, dst_dir: str) -> str:
        """Move a file into a directory.

        The file keeps its own name at the destination, and the directory is
        created if it does not exist.

        Args:
            src: URI of the file to move.
            dst_dir: URI of the directory to move it into.

        Returns:
            The full URI of the moved file.
        """

    @abstractmethod
    def copy_obj(self, src: str, dst_dir: str) -> str:
        """Copy a file into a directory, leaving the original in place.

        The copy keeps the source's name, and the directory is created if it does
        not exist.

        Args:
            src: URI of the file to copy.
            dst_dir: URI of the directory to copy it into.

        Returns:
            The full URI of the copy.
        """

    @abstractmethod
    def delete_obj(self, uri: str) -> None:
        """Delete a file.

        A file that is already absent is not an error.

        Args:
            uri: URI of the file to delete.
        """
