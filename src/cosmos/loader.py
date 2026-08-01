from pathlib import Path

from pydantic import TypeAdapter

from cosmos.engines import Engine
from cosmos.utils.yaml_loader import YamlLoader

_ADAPTER: TypeAdapter[Engine] = TypeAdapter(Engine)


def from_yaml(file_path: str | Path) -> Engine:
    """Load an engine configuration from a YAML file.

    Args:
        file_path (str | Path): The path or string representation of the YAML file to load.
    """
    config = YamlLoader(file_path=file_path).load_yaml()
    return _ADAPTER.validate_python(config)
