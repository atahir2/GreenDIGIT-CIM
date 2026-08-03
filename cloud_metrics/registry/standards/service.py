"""Standards Registry — placeholder service (Milestone 1 skeleton).

Runtime seeding/linking still lives in
``cloud_metrics.services.standards_registry``.
"""

from __future__ import annotations

from typing import List, Optional

from cloud_metrics.registry.base import RegistryName, SKELETON_ONLY
from cloud_metrics.registry.standards.types import StandardEntry


class StandardsRegistryService:
    """Placeholder Standards Registry service."""

    registry_name = RegistryName.STANDARDS
    skeleton_only = SKELETON_ONLY

    def list_entries(self) -> List[StandardEntry]:
        return []

    def get_by_code(self, code: str) -> Optional[StandardEntry]:
        return None

    def register(self, entry: StandardEntry) -> StandardEntry:
        return entry


def get_standards_registry_service() -> StandardsRegistryService:
    return StandardsRegistryService()
