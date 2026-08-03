"""Metric Registry — placeholder service (Milestone 1 skeleton).

Not connected to ingestion or persistence. Existing MetricDefinition ORM and
insert_* helpers remain the runtime path.
"""

from __future__ import annotations

from typing import List, Optional

from cloud_metrics.registry.base import RegistryName, SKELETON_ONLY
from cloud_metrics.registry.metric.types import MetricEntry


class MetricRegistryService:
    """Placeholder Metric Registry service."""

    registry_name = RegistryName.METRIC
    skeleton_only = SKELETON_ONLY

    def list_entries(self) -> List[MetricEntry]:
        return []

    def get_by_namespace(self, namespace: str) -> Optional[MetricEntry]:
        return None

    def register(self, entry: MetricEntry) -> MetricEntry:
        """Skeleton stub — persistence arrives in a later milestone."""
        return entry


def get_metric_registry_service() -> MetricRegistryService:
    return MetricRegistryService()
