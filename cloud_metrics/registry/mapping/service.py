"""Mapping Registry — placeholder service (Milestone 1 skeleton).

Runtime mapping resolution currently lives in
``cloud_metrics.services.mapping_registry_service`` and the legacy helper
``cloud_metrics.registry.mapping_registry``. This module is not wired to
ingestion in Milestone 1.
"""

from __future__ import annotations

from typing import List, Optional

from cloud_metrics.registry.base import RegistryName, SKELETON_ONLY
from cloud_metrics.registry.mapping.types import MappingEntry


class MappingRegistryService:
    """Placeholder Mapping Registry service."""

    registry_name = RegistryName.MAPPING
    skeleton_only = SKELETON_ONLY

    def list_entries(self) -> List[MappingEntry]:
        return []

    def resolve(self, source_key: str) -> Optional[MappingEntry]:
        return None

    def propose(self, entry: MappingEntry) -> MappingEntry:
        return entry


def get_mapping_registry_service() -> MappingRegistryService:
    return MappingRegistryService()
