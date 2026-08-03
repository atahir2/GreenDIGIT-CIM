"""Lifecycle Registry — placeholder service (Milestone 1 skeleton).

No lifecycle behaviour is introduced in Milestone 1.
"""

from __future__ import annotations

from typing import List, Optional

from cloud_metrics.registry.base import RegistryName, SKELETON_ONLY
from cloud_metrics.registry.lifecycle.types import LifecycleStageEntry


class LifecycleRegistryService:
    """Placeholder Lifecycle Registry service."""

    registry_name = RegistryName.LIFECYCLE
    skeleton_only = SKELETON_ONLY

    def list_entries(self) -> List[LifecycleStageEntry]:
        return []

    def get_by_stage(self, stage: str) -> Optional[LifecycleStageEntry]:
        return None

    def link_metric(self, stage: str, metric_namespace: str) -> None:
        return None


def get_lifecycle_registry_service() -> LifecycleRegistryService:
    return LifecycleRegistryService()
