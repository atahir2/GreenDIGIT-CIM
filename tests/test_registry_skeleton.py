"""Smoke tests for the Milestone 1 registry skeleton.

These tests verify package importability and placeholder service construction.
They intentionally do not touch ingestion, database schema, or mapping migration.
"""

from __future__ import annotations

import importlib

import pytest

from cloud_metrics.registry import (
    REGISTRY_MODULES,
    RegistryName,
    SKELETON_ONLY,
    get_all_registry_services,
)
from cloud_metrics.registry.base import RegistryService


EXPECTED_PACKAGES = (
    "cloud_metrics.registry.metric",
    "cloud_metrics.registry.unit",
    "cloud_metrics.registry.source",
    "cloud_metrics.registry.asset",
    "cloud_metrics.registry.standards",
    "cloud_metrics.registry.mapping",
    "cloud_metrics.registry.lifecycle",
    "cloud_metrics.registry.rule",
    "cloud_metrics.registry.evidence",
    "cloud_metrics.registry.provenance",
    "cloud_metrics.registry.extension",
)

EXPECTED_SERVICE_MODULES = (
    "cloud_metrics.services.metric_registry_service",
    "cloud_metrics.services.source_registry_service",
    "cloud_metrics.services.asset_registry_service",
    "cloud_metrics.services.lifecycle_registry_service",
    "cloud_metrics.services.evidence_registry_service",
    "cloud_metrics.services.extension_registry_service",
    # Pre-existing Antigravity services (must remain importable)
    "cloud_metrics.services.unit_registry_service",
    "cloud_metrics.services.mapping_registry_service",
    "cloud_metrics.services.rule_registry_service",
    "cloud_metrics.services.provenance_registry_service",
    "cloud_metrics.services.standards_registry",
)


@pytest.mark.parametrize("module_path", EXPECTED_PACKAGES)
def test_registry_package_imports(module_path: str):
    mod = importlib.import_module(module_path)
    assert mod is not None


@pytest.mark.parametrize("module_path", EXPECTED_SERVICE_MODULES)
def test_registry_service_module_imports(module_path: str):
    mod = importlib.import_module(module_path)
    assert mod is not None


def test_all_eleven_registries_present():
    assert len(REGISTRY_MODULES) == 11
    assert set(REGISTRY_MODULES) == set(RegistryName)


def test_placeholder_services_construct_and_list_empty():
    services = get_all_registry_services()
    assert len(services) == 11
    for name, service in services.items():
        assert service.registry_name == name
        assert service.skeleton_only is True
        assert SKELETON_ONLY is True
        assert isinstance(service, RegistryService)
        assert service.list_entries() == []


def test_metric_entry_type_constructs():
    from cloud_metrics.registry.metric import MetricEntry

    entry = MetricEntry(
        namespace="gd.energy.consumption.total_kwh",
        label="Total energy consumption",
        domain="energy",
        metric_type="observed",
    )
    assert entry.namespace.startswith("gd.")
    assert entry.status == "draft"


def test_legacy_registry_helpers_still_importable():
    """Milestone 1 must not remove or break legacy registry helpers."""
    from cloud_metrics.registry import namespace_registry, mapping_registry

    assert hasattr(namespace_registry, "ensure_gd_namespace")
    assert hasattr(mapping_registry, "register_mapping")


def test_placeholder_service_facades_list_empty():
    from cloud_metrics.services.metric_registry_service import list_metrics
    from cloud_metrics.services.source_registry_service import list_sources
    from cloud_metrics.services.asset_registry_service import list_assets
    from cloud_metrics.services.lifecycle_registry_service import list_lifecycle_stages
    from cloud_metrics.services.evidence_registry_service import list_evidence_requirements
    from cloud_metrics.services.extension_registry_service import list_extensions

    assert list_metrics() == []
    assert list_sources() == []
    assert list_assets() == []
    assert list_lifecycle_stages() == []
    assert list_evidence_requirements() == []
    assert list_extensions() == []
