from typing import Annotated

from pydantic import Field

from cosmos.storages.local import LocalStorage

StorageBackend = Annotated[
    LocalStorage,
    Field(discriminator="storage"),
]

__all__ = ["StorageBackend", "LocalStorage"]
