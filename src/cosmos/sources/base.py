from abc import ABC, abstractmethod

from cosmos.sources.models import SourceConfig


class BaseSourceReader(ABC):
    """Base class for all data sources.

    This class can be extended to implement specific logic for different types of data sources
    (e.g., local files, cloud storage, databases). It provides a common interface and structure
    for all source implementations.
    """

    def __init__(self, config: SourceConfig) -> None:
        """Initializes the reader with config.

        Args:
            config (SourceConfig): Pydantic model for source configuration.
        """
        self.config = config

    @abstractmethod
    def read(self) -> None:
        """Read the data from the source.

        This method should be implemented by all subclasses to define how the data is read
        from the source and made available for processing. The implementation will depend on
        the specific type of source and its associated logic.
        """
        pass
