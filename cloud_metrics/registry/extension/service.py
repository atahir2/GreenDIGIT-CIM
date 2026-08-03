"""Extension Registry — placeholder service (Milestone 1 skeleton).

No extension-metric behaviour is introduced in Milestone 1.
"""

from __future__ import annotations

from typing import List, Optional

from cloud_metrics.registry.base import RegistryName, SKELETON_ONLY
from cloud_metrics.registry.extension.types import ExtensionEntry


class ExtensionRegistryService:
    """Placeholder Extension Registry service."""

    registry_name = RegistryName.EXTENSION
    skeleton_only = SKELETON_ONLY

    def list_entries(self) -> List[ExtensionEntry]:
        return []

    def propose(self, entry: ExtensionEntry) -> ExtensionEntry:
        return entry

    def get_by_id(self, extension_id: int) -> Optional[ExtensionEntry]:
        return None


def get_extension_registry_service() -> ExtensionRegistryService:
    return ExtensionRegistryService()
