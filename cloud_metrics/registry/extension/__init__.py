"""Extension Registry package (Milestone 9)."""

from cloud_metrics.registry.extension.types import ExtensionEntry
from cloud_metrics.registry.extension.service import (
    ExtensionRegistryService,
    get_extension_registry_service,
    suggest_extension_namespace,
)

__all__ = [
    "ExtensionEntry",
    "ExtensionRegistryService",
    "get_extension_registry_service",
    "suggest_extension_namespace",
]
