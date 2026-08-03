"""Provenance Registry — placeholder service (Milestone 1 skeleton).

Runtime logging currently lives in
``cloud_metrics.services.provenance_registry_service``. Milestone 1 does not
change provenance behaviour.
"""

from __future__ import annotations

from typing import List, Optional

from cloud_metrics.registry.base import RegistryName, SKELETON_ONLY
from cloud_metrics.registry.provenance.types import ProvenanceEntry


class ProvenanceRegistryService:
    """Placeholder Provenance Registry service."""

    registry_name = RegistryName.PROVENANCE
    skeleton_only = SKELETON_ONLY

    def list_entries(self) -> List[ProvenanceEntry]:
        return []

    def record(self, entry: ProvenanceEntry) -> ProvenanceEntry:
        return entry

    def get_chain(
        self, entity_type: str, entity_id: int
    ) -> List[ProvenanceEntry]:
        return []


def get_provenance_registry_service() -> ProvenanceRegistryService:
    return ProvenanceRegistryService()
