"""Source Registry service placeholder (Milestone 1).

Delegates to the modular skeleton under ``cloud_metrics.registry.source``.
Not connected to ingestion.
"""

from __future__ import annotations

from typing import List, Optional

from cloud_metrics.registry.source import (
    SourceEntry,
    SourceRegistryService,
    get_source_registry_service,
)

__all__ = [
    "SourceEntry",
    "SourceRegistryService",
    "get_source_registry_service",
    "list_sources",
    "get_source_by_name",
]


def list_sources() -> List[SourceEntry]:
    return get_source_registry_service().list_entries()


def get_source_by_name(name: str) -> Optional[SourceEntry]:
    return get_source_registry_service().get_by_name(name)
