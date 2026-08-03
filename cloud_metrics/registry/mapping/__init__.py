"""Mapping Registry package (modular skeleton).

Note: legacy ``cloud_metrics.registry.mapping_registry`` remains unchanged.
"""

from cloud_metrics.registry.mapping.types import MappingEntry
from cloud_metrics.registry.mapping.service import (
    MappingRegistryService,
    get_mapping_registry_service,
)

__all__ = [
    "MappingEntry",
    "MappingRegistryService",
    "get_mapping_registry_service",
]
