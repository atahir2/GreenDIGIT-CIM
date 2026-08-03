"""Metric Registry package."""

from cloud_metrics.registry.metric.types import MetricEntry
from cloud_metrics.registry.metric.service import (
    MetricRegistryService,
    get_metric_registry_service,
)

__all__ = [
    "MetricEntry",
    "MetricRegistryService",
    "get_metric_registry_service",
]
