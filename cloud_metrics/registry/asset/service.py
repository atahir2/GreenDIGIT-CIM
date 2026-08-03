"""Asset Registry — placeholder service (Milestone 1 skeleton)."""

from __future__ import annotations

from typing import List, Optional

from cloud_metrics.registry.base import RegistryName, SKELETON_ONLY
from cloud_metrics.registry.asset.types import AssetEntry


class AssetRegistryService:
    """Placeholder Asset Registry service."""

    registry_name = RegistryName.ASSET
    skeleton_only = SKELETON_ONLY

    def list_entries(self) -> List[AssetEntry]:
        return []

    def get_by_id(self, asset_id: int) -> Optional[AssetEntry]:
        return None

    def get_hierarchy(self, asset_id: int) -> List[AssetEntry]:
        return []

    def register(self, entry: AssetEntry) -> AssetEntry:
        return entry


def get_asset_registry_service() -> AssetRegistryService:
    return AssetRegistryService()
