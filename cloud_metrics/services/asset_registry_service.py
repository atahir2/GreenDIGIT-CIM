"""Asset Registry service placeholder (Milestone 1).

Delegates to the modular skeleton under ``cloud_metrics.registry.asset``.
Not connected to ingestion. Existing ``Datacenter`` / ``insert_datacenter``
paths remain unchanged.
"""

from __future__ import annotations

from typing import List, Optional

from cloud_metrics.registry.asset import (
    AssetEntry,
    AssetRegistryService,
    get_asset_registry_service,
)

__all__ = [
    "AssetEntry",
    "AssetRegistryService",
    "get_asset_registry_service",
    "list_assets",
    "get_asset_by_id",
]


def list_assets() -> List[AssetEntry]:
    return get_asset_registry_service().list_entries()


def get_asset_by_id(asset_id: int) -> Optional[AssetEntry]:
    return get_asset_registry_service().get_by_id(asset_id)
