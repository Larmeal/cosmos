from typing import Annotated

from pydantic import Field

from pylos.sources.gcs import GCSSourceConfig
from pylos.sources.local import LocalSourceConfig

SourceConfig = Annotated[
    LocalSourceConfig | GCSSourceConfig,
    Field(discriminator="storage"),
]
