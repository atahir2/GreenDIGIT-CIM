"""Evidence Registry — placeholder service (Milestone 1 skeleton).

No evidence behaviour is introduced in Milestone 1.
"""

from __future__ import annotations

from typing import List, Optional

from cloud_metrics.registry.base import RegistryName, SKELETON_ONLY
from cloud_metrics.registry.evidence.types import EvidenceRequirementEntry


class EvidenceRegistryService:
    """Placeholder Evidence Registry service."""

    registry_name = RegistryName.EVIDENCE
    skeleton_only = SKELETON_ONLY

    def list_entries(self) -> List[EvidenceRequirementEntry]:
        return []

    def get_by_id(self, requirement_id: int) -> Optional[EvidenceRequirementEntry]:
        return None

    def register(self, entry: EvidenceRequirementEntry) -> EvidenceRequirementEntry:
        return entry


def get_evidence_registry_service() -> EvidenceRegistryService:
    return EvidenceRegistryService()
