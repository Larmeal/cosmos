from typing import Annotated

from pydantic import Field

from pylos.storages.local import LocalStorage

StorageBackend = Annotated[
    LocalStorage,
    Field(discriminator="storage"),
]

__all__ = ["StorageBackend", "LocalStorage"]
