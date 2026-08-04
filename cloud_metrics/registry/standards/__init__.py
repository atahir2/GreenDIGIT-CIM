"""Standards Registry package (Milestone 8)."""

from cloud_metrics.registry.standards.types import (
    RELATION_TYPES,
    STRONG_IDENTITY_RELATIONS,
    StandardEntry,
    StandardMappingEntry,
    StandardsLookupResult,
)
from cloud_metrics.registry.standards.service import (
    StandardsRegistryService,
    get_standards_registry_service,
)

__all__ = [
    "RELATION_TYPES",
    "STRONG_IDENTITY_RELATIONS",
    "StandardEntry",
    "StandardMappingEntry",
    "StandardsLookupResult",
    "StandardsRegistryService",
    "get_standards_registry_service",
]
