"""Source Registry — placeholder service (Milestone 1 skeleton)."""

from __future__ import annotations

from typing import List, Optional

from cloud_metrics.registry.base import RegistryName, SKELETON_ONLY
from cloud_metrics.registry.source.types import SourceEntry


class SourceRegistryService:
    """Placeholder Source Registry service."""

    registry_name = RegistryName.SOURCE
    skeleton_only = SKELETON_ONLY

    def list_entries(self) -> List[SourceEntry]:
        return []

    def get_by_name(self, name: str) -> Optional[SourceEntry]:
        return None

    def register(self, entry: SourceEntry) -> SourceEntry:
        return entry


def get_source_registry_service() -> SourceRegistryService:
    return SourceRegistryService()
