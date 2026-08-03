"""Milestone 3: idempotent ``cim_*`` registry seed tests."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from cloud_metrics.models.cim_registry import (
    CimEvidenceRequirement,
    CimLifecycleStage,
    CimMetricDefinition,
    CimMetricLifecycleLink,
    CimMetricMapping,
    CimQuantityKind,
    CimStandard,
    CimUnit,
    CimValidationRule,
)
from cloud_metrics.registry.seed import RELATION_TYPES, seed_all
from cloud_metrics.registry.seed import data as seed_data


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
def seeded_session():
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
    report = seed_all(session, commit=True)
    yield session, report, engine

    session.close()
    with engine.begin() as conn:
        ctx = MigrationContext.configure(conn)
        with Operations.context(ctx):
            migration.downgrade()


def test_seed_runs_successfully(seeded_session):
    session, report, _ = seeded_session
    assert report.created.get("metrics", 0) == len(seed_data.METRICS)
    assert report.created.get("quantity_kinds", 0) == len(seed_data.QUANTITY_KINDS)
    assert report.created.get("units", 0) == len(seed_data.UNITS)
    assert report.created.get("lifecycle_stages", 0) == len(seed_data.LIFECYCLE_STAGES)
    assert report.created.get("standards", 0) == len(seed_data.STANDARDS)
    assert session.query(CimMetricDefinition).count() == len(seed_data.METRICS)


def test_seed_is_idempotent(seeded_session):
    session, first, _ = seeded_session
    metric_count = session.query(CimMetricDefinition).count()
    unit_count = session.query(CimUnit).count()
    link_count = session.query(CimMetricLifecycleLink).count()
    map_count = session.query(CimMetricMapping).count()
    rule_count = session.query(CimValidationRule).count()
    evidence_count = session.query(CimEvidenceRequirement).count()

    second = seed_all(session, commit=True)

    assert session.query(CimMetricDefinition).count() == metric_count
    assert session.query(CimUnit).count() == unit_count
    assert session.query(CimMetricLifecycleLink).count() == link_count
    assert session.query(CimMetricMapping).count() == map_count
    assert session.query(CimValidationRule).count() == rule_count
    assert session.query(CimEvidenceRequirement).count() == evidence_count

    # Second pass should report existing rows, not create duplicates
    assert second.created.get("metrics", 0) == 0
    assert second.existing.get("metrics", 0) == len(seed_data.METRICS)
    assert first.created.get("metrics", 0) == len(seed_data.METRICS)


def test_seeded_metrics_have_required_fields(seeded_session):
    session, _, _ = seeded_session
    metrics = session.query(CimMetricDefinition).all()
    assert metrics
    for m in metrics:
        assert m.namespace
        assert m.namespace.startswith("cim:")
        assert m.label
        assert m.domain
        assert m.category
        assert m.subcategory
        assert m.quantity_kind_id is not None
        assert m.canonical_unit_id is not None
        assert m.metric_type
        assert m.status == "approved"
        assert m.review_status == "approved"
        assert m.version == 1


def test_units_linked_to_quantity_kinds(seeded_session):
    session, _, _ = seeded_session
    for symbol in ("W", "kW", "Wh", "kWh", "J", "kgCO2e", "gCO2e", "gCO2e/kWh",
                   "s", "ms", "h", "B", "KB", "MB", "GB", "TB", "%", "ratio",
                   "score", "dimensionless", "L", "m3", "count"):
        unit = session.query(CimUnit).filter_by(symbol=symbol).one()
        assert unit.quantity_kind_id is not None
        qk = session.get(CimQuantityKind, unit.quantity_kind_id)
        assert qk is not None


def test_lifecycle_stages_queryable(seeded_session):
    session, _, _ = seeded_session
    keys = {s.stage_key for s in session.query(CimLifecycleStage).all()}
    expected = {s["stage_key"] for s in seed_data.LIFECYCLE_STAGES}
    assert keys == expected


def test_standards_queryable(seeded_session):
    session, _, _ = seeded_session
    codes = {s.code for s in session.query(CimStandard).all()}
    expected = {s["code"] for s in seed_data.STANDARDS}
    assert codes == expected


def test_metric_lifecycle_links_created(seeded_session):
    session, _, _ = seeded_session
    expected_pairs = sum(len(v) for v in seed_data.METRIC_LIFECYCLE_LINKS.values())
    assert session.query(CimMetricLifecycleLink).count() == expected_pairs

    pue = session.query(CimMetricDefinition).filter_by(
        namespace="cim:energy.efficiency.pue"
    ).one()
    links = session.query(CimMetricLifecycleLink).filter_by(metric_id=pue.id).all()
    stage_ids = {lnk.lifecycle_stage_id for lnk in links}
    stages = {
        s.stage_key
        for s in session.query(CimLifecycleStage).filter(
            CimLifecycleStage.id.in_(stage_ids)
        )
    }
    assert stages == {"operation", "reporting", "continuous_improvement"}


def test_safe_standards_mappings_created(seeded_session):
    session, _, _ = seeded_session
    assert session.query(CimMetricMapping).count() == len(seed_data.STANDARD_MAPPINGS)

    pue = session.query(CimMetricDefinition).filter_by(
        namespace="cim:energy.efficiency.pue"
    ).one()
    maps = session.query(CimMetricMapping).filter_by(metric_id=pue.id).all()
    assert len(maps) >= 2
    assert all(m.origin == "seeded" for m in maps)
    assert {m.relation_type for m in maps} == {"exactMatch"}


def test_validation_rules_queryable(seeded_session):
    session, _, _ = seeded_session
    names = {r.name for r in session.query(CimValidationRule).all()}
    expected = {r["name"] for r in seed_data.VALIDATION_RULES}
    assert names == expected


def test_evidence_requirements_queryable(seeded_session):
    session, _, _ = seeded_session
    assert session.query(CimEvidenceRequirement).count() == len(
        seed_data.EVIDENCE_REQUIREMENTS
    )


def test_relation_types_vocabulary_documented():
    required = {
        "exactMatch",
        "closeMatch",
        "broadMatch",
        "narrowMatch",
        "inputToKPI",
        "derivedFrom",
        "contextualMatch",
        "extensionMetric",
        "noMatch",
        "underReview",
    }
    assert set(RELATION_TYPES) == required


def test_no_duplicate_namespaces_after_double_seed(seeded_session):
    session, _, _ = seeded_session
    seed_all(session, commit=True)
    dupes = (
        session.query(
            CimMetricDefinition.namespace,
            func.count(CimMetricDefinition.id),
        )
        .group_by(CimMetricDefinition.namespace)
        .having(func.count(CimMetricDefinition.id) > 1)
        .all()
    )
    assert dupes == []
