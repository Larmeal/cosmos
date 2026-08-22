from typing import Annotated

from pydantic import Field

from cosmos.storage.local import LocalStorage

StorageBackend = Annotated[
    LocalStorage,
    Field(discriminator="storage"),
]
