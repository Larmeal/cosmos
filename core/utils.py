from pathlib import Path

from pydantic import BaseModel, Field, field_validator
from yaml import safe_load


class YamlLoader(BaseModel):
    """
    A loader class for YAML files.
    """

    file_path: Path | str
    configuration: dict = Field(default_factory=dict)

    @field_validator("file_path")
    @classmethod
    def validate_file_path(cls, value: Path | str) -> Path:
        """Validate the file path to ensure it exists and is a file.

        Args:
            value (Path | str): The file path to validate.

        Returns:
            Path: The validated file path.

        Raises:
            ValueError: If the file path does not exist or is not a file.
        """
        path_obj = Path(value) if isinstance(value, str) else value
        if not path_obj.is_file():
            raise ValueError(f"The path '{path_obj}' does not exist or is not a file.")
        return path_obj

    @field_validator("file_path")
    @classmethod
    def validate_file_extension(cls, value: Path) -> Path:
        """Validate the file extension to ensure it is a YAML file.

        Args:
            value (Path): The file path to validate.

        Returns:
            Path: The validated file path.

        Raises:
            ValueError: If the file extension is not .yaml or .yml.
        """
        if value.suffix not in {".yaml", ".yml"}:
            raise ValueError(
                f"The provided path '{value}' does not have a valid YAML extension."
            )
        return value

    def load_yaml(self) -> dict:
        """Reads the YAML file and parses it into a dictionary.

        Returns:
            A dictionary containing the parsed YAML configuration.
        """
        with open(self.file_path, encoding="utf-8") as file:
            return safe_load(file)
