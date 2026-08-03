"""Asset Registry package."""

from cloud_metrics.registry.asset.types import AssetEntry
from cloud_metrics.registry.asset.service import (
    AssetRegistryService,
    get_asset_registry_service,
)

__all__ = [
    "AssetEntry",
    "AssetRegistryService",
    "get_asset_registry_service",
]
