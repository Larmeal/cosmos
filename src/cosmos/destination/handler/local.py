import json
import logging
import shutil
from pathlib import Path

from cosmos.destination.base import BaseFailureHandler
from cosmos.destination.models import (
    DeleteFailureAction,
    IgnoreFailureAction,
    RelocateFailureAction,
)

logger = logging.getLogger(__name__)


class LocalFailureHandler(BaseFailureHandler):
    """Handles failure actions for local file systems using pathlib."""

    def _save_metadata(self, dest_path: Path, custom_metadata: dict) -> None:
        """Helper method to save the custom JSON metadata alongside the failed file.

        Args:
            dest_path: The pathlib.Path object representing the destination file.
            custom_metadata: The custom system metadata to save as JSON.
        """

        meta_path = dest_path / f"{dest_path.stem}_meta.json"
        meta_path.parent.mkdir(parents=True, exist_ok=True)

        with meta_path.open("w", encoding="utf-8") as f:
            json.dump(custom_metadata, f, indent=4)

        logger.info(f"Custom failure metadata saved to: {meta_path}")

    def execute(
        self,
        source_path: str,
        custom_metadata: dict,
    ) -> None:
        """Executes the specific local file operation safely using Pattern Matching."""
        src_p = Path(source_path)

        match self.config:
            case IgnoreFailureAction():
                logger.info(
                    "Failure action is 'ignore'. Leaving the source file untouched."
                )

            case DeleteFailureAction():
                # .exists() and .unlink() are built directly into the Path object
                if src_p.exists():
                    src_p.unlink()
                    logger.info(f"Deleted source file: {src_p}")
                else:
                    logger.warning(f"File to delete not found: {src_p}")

            case RelocateFailureAction() as relocate:
                dest_p = Path(relocate.dir_path)

                # Ensure the destination directory exists before moving/copying
                try:
                    dest_p.mkdir(parents=True, exist_ok=True)
                except PermissionError:
                    logger.error(
                        f"Permission denied: Cannot create directory at '{dest_p}'."
                    )
                    raise

                match relocate.action:
                    case "metadata_only":
                        logger.info("Saving metadata without moving the source file.")
                        self._save_metadata(dest_p, custom_metadata)

                    case "move_file":
                        logger.info(f"Moving file from {src_p} to {dest_p}")
                        # shutil still works perfectly with pathlib objects
                        shutil.move(src_p, dest_p)
                        self._save_metadata(dest_p, custom_metadata)

                    case "copy_file":
                        logger.info(f"Copying file from {src_p} to {dest_p}")
                        shutil.copy2(src_p, dest_p)
                        self._save_metadata(dest_p, custom_metadata)
