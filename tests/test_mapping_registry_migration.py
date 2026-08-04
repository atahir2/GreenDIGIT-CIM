"""Milestone 4: legacy mapping migration + registry-first lookup tests."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from cloud_metrics.models.cim_registry import CimMetricDefinition, CimMetricMapping
from cloud_metrics.registry.mapping import (
    MappingRegistryService,
    resolve_raw_metric,
)
from cloud_metrics.registry.migration import (
    discover_legacy_mappings,
    migrate_legacy_mappings,
)
from cloud_metrics.registry.migration.gd_to_cim import resolve_cim_namespace
from cloud_metrics.registry.migration.legacy_sources import LegacyMappingRecord
from cloud_metrics.registry.seed import seed_all


M2_FILE = (
    Path(__file__).resolve().parents[1]
    / "migrations"
    / "versions"
    / "c2f8a1b9e047_add_cim_registry_tables.py"
)


def _load_m2():
    spec = importlib.util.spec_from_file_location("cim_m2_migration", M2_FILE)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture()
def cim_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    migration = _load_m2()
    with engine.begin() as conn:
        ctx = MigrationContext.configure(conn)
        with Operations.context(ctx):
            migration.upgrade()

    Session = sessionmaker(bind=engine, future=True)
    session = Session()
    seed_all(session, commit=True)
    yield session

    session.close()
    with engine.begin() as conn:
        ctx = MigrationContext.configure(conn)
        with Operations.context(ctx):
            migration.downgrade()


# ---------------------------------------------------------------------------
# Discovery / namespace translation
# ---------------------------------------------------------------------------


def test_discover_legacy_mappings_finds_known_sources():
    report = discover_legacy_mappings()
    assert len(report.records) > 0
    sources = set(report.by_source)
    assert "mapping_json" in sources or "alias_classifier" in sources
    assert "alias_seeds" in sources or "alias_classifier" in sources
    raws = {r.raw_key.lower() for r in report.records}
    # Known alias / JSON keys that should survive noise filtering
    assert "energy_wh" in raws or "pue" in raws


def test_gd_to_cim_trusted_alignments():
    ns, trusted = resolve_cim_namespace("gd.energy.efficiency.pue")
    assert ns == "cim:energy.efficiency.pue"
    assert trusted is True

    ns2, trusted2 = resolve_cim_namespace("gd.network.traffic.incoming")
    assert ns2 == "cim:network.traffic.ingress"
    assert trusted2 is True

    ns3, trusted3 = resolve_cim_namespace("gd.performance.cpu.tdp")
    assert ns3 == "cim:performance.cpu.tdp"
    assert trusted3 is False


# ---------------------------------------------------------------------------
# Migration
# ---------------------------------------------------------------------------


def test_migrate_known_raw_maps_to_same_cim_namespace(cim_session):
    """energy_wh historically maps to gd.energy.consumption.total → cim:*."""
    report = migrate_legacy_mappings(cim_session, commit=True)
    assert report.mappings_created > 0

    row = (
        cim_session.query(CimMetricMapping)
        .filter(func.lower(CimMetricMapping.source_key) == "energy_wh")
        .first()
    )
    assert row is not None
    metric = cim_session.get(CimMetricDefinition, row.metric_id)
    assert metric is not None
    assert metric.namespace == "cim:energy.consumption.total"
    assert row.status == "approved"


def test_registry_lookup_succeeds_for_migrated_mappings(cim_session):
    migrate_legacy_mappings(cim_session, commit=True)
    svc = MappingRegistryService(session=cim_session)
    entry = svc.resolve("pue")
    assert entry is not None
    assert entry.cim_namespace == "cim:energy.efficiency.pue"
    assert entry.status == "approved"

    result = resolve_raw_metric("pue", session=cim_session, use_fallback=False)
    assert result.resolved is True
    assert result.resolution_path == "registry"
    assert result.cim_namespace == "cim:energy.efficiency.pue"


def test_duplicate_migration_does_not_create_duplicates(cim_session):
    first = migrate_legacy_mappings(cim_session, commit=True)
    mapping_count = cim_session.query(CimMetricMapping).count()
    metric_count = cim_session.query(CimMetricDefinition).count()

    second = migrate_legacy_mappings(cim_session, commit=True)

    assert cim_session.query(CimMetricMapping).count() == mapping_count
    assert cim_session.query(CimMetricDefinition).count() == metric_count
    assert second.mappings_created == 0
    assert second.mappings_skipped_duplicate == first.mappings_created
    assert second.candidate_metrics_created == 0


def test_candidate_metric_created_when_namespace_missing(cim_session):
    # Use a synthetic legacy record whose gd.* has no approved cim:* seed
    discovery_records = [
        LegacyMappingRecord(
            raw_key="synthetic_tdp_raw",
            legacy_unified_key="gd.performance.cpu.tdp",
            source_name="test_fixture",
            confidence=0.9,
            category="performance",
            subcategory="cpu",
            short_key="tdp",
            notes="synthetic candidate test",
        )
    ]
    from cloud_metrics.registry.migration.legacy_sources import DiscoveryReport

    disc = DiscoveryReport(records=discovery_records)
    before = (
        cim_session.query(CimMetricDefinition)
        .filter_by(namespace="cim:performance.cpu.tdp")
        .count()
    )
    assert before == 0

    report = migrate_legacy_mappings(cim_session, discovery=disc, commit=True)
    assert report.candidate_metrics_created == 1

    metric = (
        cim_session.query(CimMetricDefinition)
        .filter_by(namespace="cim:performance.cpu.tdp")
        .one()
    )
    assert metric.status == "candidate"
    assert metric.review_status == "under_review"

    mapping = (
        cim_session.query(CimMetricMapping)
        .filter_by(source_key="synthetic_tdp_raw")
        .one()
    )
    assert mapping.status == "candidate"
    assert mapping.review_status == "under_review"
    assert mapping.metric_id == metric.id


# ---------------------------------------------------------------------------
# Lookup fallback / unresolved
# ---------------------------------------------------------------------------


def test_legacy_fallback_when_registry_entry_missing(cim_session):
    """Without migration, JSON/alias fallback still resolves known keys."""
    # Ensure no cim_metric_mappings row for this raw key (except std: seeds)
    existing = (
        cim_session.query(CimMetricMapping)
        .filter(func.lower(CimMetricMapping.source_key) == "alpha.cpu")
        .first()
    )
    assert existing is None

    result = resolve_raw_metric(
        "alpha.cpu",
        session=cim_session,
        use_fallback=True,
        create_candidate_on_fallback=False,
    )
    assert result.resolved is True
    assert result.resolution_path == "legacy_fallback"
    assert result.cim_namespace == "cim:compute.cpu.utilisation"
    assert result.legacy_unified_key == "gd.performance.cpu.utilization"
    assert result.status == "candidate"


def test_unknown_raw_metric_returns_unresolved(cim_session):
    result = resolve_raw_metric(
        "totally_unknown_metric_xyz_999",
        session=cim_session,
        use_fallback=True,
    )
    assert result.resolved is False
    assert result.resolution_path == "unresolved"
    assert result.status == "unresolved"
    assert result.cim_namespace is None


def test_fallback_can_create_candidate_mapping(cim_session):
    result = resolve_raw_metric(
        "alpha.mem",
        session=cim_session,
        use_fallback=True,
        create_candidate_on_fallback=True,
    )
    assert result.resolved is True
    assert result.resolution_path == "legacy_fallback"
    assert result.candidate_created is True
    assert result.cim_namespace == "cim:compute.memory.usage"

    row = (
        cim_session.query(CimMetricMapping)
        .filter(func.lower(CimMetricMapping.source_key) == "alpha.mem")
        .first()
    )
    assert row is not None
    assert row.status == "candidate"


def test_skeleton_without_session_still_empty():
    """Milestone 1 contract: no session → empty list / None resolve."""
    svc = MappingRegistryService()
    assert svc.list_entries() == []
    assert svc.resolve("pue") is None
