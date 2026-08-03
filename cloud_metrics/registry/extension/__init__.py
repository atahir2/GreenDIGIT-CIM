"""Extension Registry package."""

from cloud_metrics.registry.extension.types import ExtensionEntry
from cloud_metrics.registry.extension.service import (
    ExtensionRegistryService,
    get_extension_registry_service,
)

__all__ = [
    "ExtensionEntry",
    "ExtensionRegistryService",
    "get_extension_registry_service",
]
