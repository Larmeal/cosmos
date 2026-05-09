from abc import ABC, abstractmethod

from cosmos.destination.models import OnFailureActionConfig


class BaseFailureHandler(ABC):
    """Abstract interface for handling raw file operations on validation failure."""

    def __init__(self, config: OnFailureActionConfig) -> None:
        """Initializes the handler with the validated action configuration."""
        self.config = config

    @abstractmethod
    def execute(self, source_path: str, custom_metadata: dict) -> None:
        """Executes the failure action using the pre-loaded configuration.

        Args:
            source_path: The original path of the source file.
            custom_metadata: The dictionary containing the parsed GX failure details.
        """
        pass
