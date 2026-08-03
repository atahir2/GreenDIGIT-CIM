"""Standards Registry package."""

from cloud_metrics.registry.standards.types import StandardEntry
from cloud_metrics.registry.standards.service import (
    StandardsRegistryService,
    get_standards_registry_service,
)

__all__ = [
    "StandardEntry",
    "StandardsRegistryService",
    "get_standards_registry_service",
]
