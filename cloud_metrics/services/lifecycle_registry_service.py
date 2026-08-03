"""Lifecycle Registry service placeholder (Milestone 1).

Delegates to the modular skeleton under ``cloud_metrics.registry.lifecycle``.
No lifecycle-stage behaviour is enforced yet.
"""

from __future__ import annotations

from typing import List, Optional

from cloud_metrics.registry.lifecycle import (
    LifecycleStageEntry,
    LifecycleRegistryService,
    get_lifecycle_registry_service,
)

__all__ = [
    "LifecycleStageEntry",
    "LifecycleRegistryService",
    "get_lifecycle_registry_service",
    "list_lifecycle_stages",
    "get_lifecycle_stage",
]


def list_lifecycle_stages() -> List[LifecycleStageEntry]:
    return get_lifecycle_registry_service().list_entries()


def get_lifecycle_stage(stage: str) -> Optional[LifecycleStageEntry]:
    return get_lifecycle_registry_service().get_by_stage(stage)
