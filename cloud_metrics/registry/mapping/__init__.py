"""Mapping Registry package.

Milestone 4 adds registry-first lookup with legacy fallback when a DB session
is supplied. Legacy ``cloud_metrics.registry.mapping_registry`` is unchanged.
"""

from cloud_metrics.registry.mapping.types import MappingEntry, MappingLookupResult
from cloud_metrics.registry.mapping.service import (
    MappingRegistryService,
    get_mapping_registry_service,
    resolve_raw_metric,
)

__all__ = [
    "MappingEntry",
    "MappingLookupResult",
    "MappingRegistryService",
    "get_mapping_registry_service",
    "resolve_raw_metric",
]
