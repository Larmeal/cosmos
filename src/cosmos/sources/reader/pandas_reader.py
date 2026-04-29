import pandas as pd

from cosmos.sources.base import BaseSourceReader


class PandasReader(BaseSourceReader):
    """Reader for loading data into a Pandas DataFrame.

    This class implements the logic to read data from various sources (e.g., CSV files, databases)
    and load it into a Pandas DataFrame for further processing and validation. It extends the
    BaseSourceReader to provide a specific implementation for the Pandas engine.
    """

    def read(self) -> pd.DataFrame:
        """Read the data from the source and return a Pandas DataFrame.

        This method reads data from the configured source and loads it into a Pandas DataFrame.
        The implementation will depend on the specific type of source and its associated logic.

        Returns:
            pd.DataFrame: The loaded data as a Pandas DataFrame.
        """

        match self.config.source.file_format.lower():
            case "csv":
                df = pd.read_csv(
                    filepath_or_buffer=self.config.source.file_path,
                    **self.config.source.options,
                )
                return df

            case "parquet":
                df = pd.read_parquet(
                    path=self.config.source.file_path,
                    **self.config.source.options,
                )
                return df

            case _:
                raise ValueError(
                    f"File format '{self.config.source.file_format}' is not supported by PandasReader."
                )
