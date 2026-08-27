from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable

from pydantic import BaseModel

from cosmos.result import SourceObjectMetadata


class BaseStorage(BaseModel, ABC):
    """Interface for file operations on a storage backend.

    One subclass per backend — local disk, GCS, S3 — each implemented with that
    backend's own SDK. ``glob`` resolves a source pattern into the files a run
    will process, each with the size and mtime the planner renders; ``move``,
    ``copy`` and ``delete`` relocate or remove a file after validation fails.

    Reading is not part of this interface: engines read by URI with their own
    readers.

    Paths are URIs in whatever form the backend uses — filesystem paths for local
    storage, ``gs://bucket/key`` for GCS.
    """

    def glob(self, pattern: str) -> list[SourceObjectMetadata]:
        """Resolve a pattern into the objects it matches, metadata included.

        Template method: the shape of the result is fixed here so every backend
        agrees on it — sorted by ``path`` for a reproducible processing order,
        directories never present. Backends supply the two halves: ``_list_files``
        walks the backend, ``_to_metadata`` turns one native entry into a
        ``SourceObjectMetadata``.

        Args:
            pattern: A glob in the backend's syntax, such as ``data/test_*.csv``.
                A pattern containing no wildcard matches only itself.

        Returns:
            The matching objects, sorted by ``path``. Empty when nothing matches,
            which ``source.on_empty`` assigns meaning to.
        """
        return sorted(
            (self._to_metadata(entry) for entry in self._list_files(pattern)),
            key=lambda meta: meta.path,
        )

    @abstractmethod
    def _list_files(self, pattern: str) -> Iterable[object]:
        """Yield one backend-native entry per matching file.

        Directories are excluded here, not downstream. The entry type is the
        backend's own — a ``Path`` for local disk, a ``Blob`` for GCS — and is
        only ever consumed by this backend's ``_to_metadata``, which narrows it.
        """

    @abstractmethod
    def _to_metadata(self, entry: object) -> SourceObjectMetadata:
        """Map one entry from ``_list_files`` to a ``SourceObjectMetadata``.

        Must populate ``path``, ``size_bytes`` and ``modified``. The entry already
        carries what is needed — a GCS ``Blob`` from a listing has ``size`` and
        ``updated`` on it — so this never issues another request.
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
