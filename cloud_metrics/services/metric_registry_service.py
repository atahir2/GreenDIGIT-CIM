"""Metric Registry service placeholder (Milestone 1).

Delegates to the modular skeleton under ``cloud_metrics.registry.metric``.
Not connected to ingestion. Existing ``insert_mapped_metric`` /
``MetricDefinition`` paths remain the runtime implementation.
"""

from __future__ import annotations

from typing import List, Optional

from cloud_metrics.registry.metric import (
    MetricEntry,
    MetricRegistryService,
    get_metric_registry_service,
)

__all__ = [
    "MetricEntry",
    "MetricRegistryService",
    "get_metric_registry_service",
    "list_metrics",
    "get_metric_by_namespace",
]


def list_metrics() -> List[MetricEntry]:
    return get_metric_registry_service().list_entries()


def get_metric_by_namespace(namespace: str) -> Optional[MetricEntry]:
    return get_metric_registry_service().get_by_namespace(namespace)
