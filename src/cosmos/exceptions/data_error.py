from .base import DataError


class SourceEmptyError(DataError):
    """Raised when a source object is empty, indicating that there is no data to process.

    ``row_count``/``column_count`` carry whatever shape was known at the moment of
    raising. A file that parsed but has no rows (just a header) knows both; a file
    that could not be parsed at all (zero bytes) knows neither, so both default to
    ``None``. The runner reports whichever this exception was raised with, since by
    the time it is caught the engine object that held the dataframe is gone.
    """

    def __init__(
        self,
        message: str,
        row_count: int | None = None,
        column_count: int | None = None,
    ) -> None:
        super().__init__(message)
        self.row_count = row_count
        self.column_count = column_count
