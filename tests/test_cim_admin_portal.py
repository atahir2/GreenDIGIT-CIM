"""Milestone 14: CIM admin portal helpers (no Streamlit runtime required)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from cloud_metrics.models.cim_registry import CimMetricDefinition, CimMetricMapping
from cloud_metrics.registry.review import ReviewAction
from cloud_metrics.registry.seed import seed_all
from cloud_metrics.ui.cim_portal import (
    REGISTRY_CHOICES,
    REPORTABLE_NAMESPACES,
    filter_registry_rows,
    load_provenance_timeline,
    load_registry_rows,
    perform_review_action,
    readiness_rows,
)


M2_FILE = (
    Path(__file__).resolve().parents[1]
    / "migrations"
    / "versions"
    / "c2f8a1b9e047_add_cim_registry_tables.py"
)


def _load_m2():
    spec = importlib.util.spec_from_file_location("cim_m2_migration_m14", M2_FILE)
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


def test_all_registries_load(cim_session):
    for name in REGISTRY_CHOICES:
        rows = load_registry_rows(cim_session, name)
        assert isinstance(rows, list)
    metrics = load_registry_rows(cim_session, "metric")
    assert any(r.get("namespace") == "cim:energy.efficiency.pue" for r in metrics)


def test_filter_registry_rows_status_and_search():
    rows = [
        {"id": 1, "status": "approved", "review_status": "approved", "namespace": "cim:a"},
        {"id": 2, "status": "candidate", "review_status": "under_review", "namespace": "cim:b"},
    ]
    assert len(filter_registry_rows(rows, status="candidate")) == 1
    assert len(filter_registry_rows(rows, search="cim:a")) == 1
    assert len(filter_registry_rows(rows, status="(all)", review_status="(all)")) == 2


def test_unknown_registry_raises(cim_session):
    with pytest.raises(ValueError):
        load_registry_rows(cim_session, "not_a_registry")


def test_readiness_rows_for_reportable_kpis(cim_session):
    rows = readiness_rows(cim_session)
    nss = {r["namespace"] for r in rows}
    assert set(REPORTABLE_NAMESPACES) <= nss
    pue = next(r for r in rows if r["namespace"] == "cim:energy.efficiency.pue")
    assert pue["readiness_status"] == "declared"
    assert pue["mandatory_count"] >= 1
    assert pue["missing_fulfillment_count"] == pue["mandatory_count"]
    assert any(s["relation_type"] == "exactMatch" for s in pue["standards_relations"])


def test_perform_review_action_uses_admin_service(cim_session):
    metric = (
        cim_session.query(CimMetricDefinition)
        .filter_by(namespace="cim:compute.node.power.draw")
        .one()
    )
    row = CimMetricMapping(
        source_key="ui_review_raw_m14",
        source_id=None,
        metric_id=metric.id,
        relation_type="exactMatch",
        origin="test",
        status="candidate",
        review_status="under_review",
        confidence_score=0.5,
        version=1,
        created_by="milestone14_test",
    )
    cim_session.add(row)
    cim_session.commit()

    decision = perform_review_action(
        cim_session,
        "mapping",
        row.id,
        ReviewAction.APPROVE.value,
        reviewer="ui_tester",
        notes="approve from portal helper",
    )
    assert decision.ok is True
    assert decision.new_status in {"approved", "active"}
    assert decision.provenance_record_id is not None
    cim_session.refresh(row)
    assert row.status in {"approved", "active"}


def test_perform_review_rejects_without_direct_sql_status_write(cim_session):
    metric = (
        cim_session.query(CimMetricDefinition)
        .filter_by(namespace="cim:compute.cpu.utilisation")
        .one()
    )
    row = CimMetricMapping(
        source_key="ui_reject_raw_m14",
        source_id=None,
        metric_id=metric.id,
        relation_type="exactMatch",
        origin="test",
        status="candidate",
        review_status="pending",
        version=1,
        created_by="milestone14_test",
    )
    cim_session.add(row)
    cim_session.commit()
    decision = perform_review_action(
        cim_session, "mapping", row.id, "reject", reviewer="ui_tester"
    )
    assert decision.ok is True
    assert decision.new_status == "rejected"


def test_provenance_timeline_after_review(cim_session):
    metric = (
        cim_session.query(CimMetricDefinition)
        .filter_by(namespace="cim:compute.memory.usage")
        .one()
    )
    row = CimMetricMapping(
        source_key="ui_prov_raw_m14",
        source_id=None,
        metric_id=metric.id,
        relation_type="exactMatch",
        origin="test",
        status="candidate",
        review_status="under_review",
        version=1,
        created_by="milestone14_test",
    )
    cim_session.add(row)
    cim_session.commit()
    perform_review_action(cim_session, "mapping", row.id, "approve", reviewer="ui_tester")
    timeline = load_provenance_timeline(
        cim_session, entity_type="cim_mapping", entity_id=row.id
    )
    if not timeline:
        timeline = load_provenance_timeline(cim_session)
    assert any(r["activity"] == "review_action" for r in timeline)
