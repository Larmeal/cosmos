from .base import DataError


class SourceEmptyError(DataError):
    """Raised when a source object is empty, indicating that there is no data to process."""
