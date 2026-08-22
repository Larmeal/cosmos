from typing import Annotated

from pydantic import Field

from cosmos.sources.gcs import GCSSourceConfig
from cosmos.sources.local import LocalSourceConfig

SourceConfig = Annotated[
    LocalSourceConfig | GCSSourceConfig,
    Field(discriminator="storage"),
]
