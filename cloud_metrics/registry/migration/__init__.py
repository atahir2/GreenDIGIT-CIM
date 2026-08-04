"""Milestone 4: migrate legacy raw→unified mappings into ``cim_*`` registries."""

from cloud_metrics.registry.migration.sync import (
    MigrationReport,
    migrate_legacy_mappings,
)
from cloud_metrics.registry.migration.legacy_sources import (
    LegacyMappingRecord,
    discover_legacy_mappings,
)

__all__ = [
    "LegacyMappingRecord",
    "MigrationReport",
    "discover_legacy_mappings",
    "migrate_legacy_mappings",
]
