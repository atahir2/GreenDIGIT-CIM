"""Milestone 2: validate cim_* registry schema migration apply/rollback.

Uses an isolated SQLite database. Exercises the Milestone 2 revision
(``c2f8a1b9e047``) upgrade/downgrade directly so tests do not depend on the
legacy Alembic chain (which assumes a pre-existing PostgreSQL schema).
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from alembic.migration import MigrationContext
from alembic.operations import Operations

from cloud_metrics.models.cim_registry import (
    CIM_REGISTRY_TABLES,
    GOVERNANCE_COLUMNS,
    CimLifecycleStage,
    CimMetricDefinition,
    CimMetricLifecycleLink,
    CimMetricMapping,
    CimQuantityKind,
    CimSource,
    CimStandard,
    CimUnit,
)
from cloud_metrics.models.db_models import Base


M2_REVISION = "c2f8a1b9e047"
M2_FILE = (
    Path(__file__).resolve().parents[1]
    / "migrations"
    / "versions"
    / "c2f8a1b9e047_add_cim_registry_tables.py"
)

REQUIRED_COLUMNS = {
    "cim_metric_definitions": {
        "namespace",
        "label",
        "domain",
        "quantity_kind_id",
        "canonical_unit_id",
        "metric_type",
        *GOVERNANCE_COLUMNS,
    },
    "cim_units": {
        "symbol",
        "name",
        "quantity_kind_id",
        "conversion_factor",
        *GOVERNANCE_COLUMNS,
    },
    "cim_quantity_kinds": {"name", *GOVERNANCE_COLUMNS},
    "cim_sources": {"name", "type", *GOVERNANCE_COLUMNS},
    "cim_assets": {"identifier", "name", "type", "parent_id", *GOVERNANCE_COLUMNS},
    "cim_standards": {"code", "name", "standard_version", *GOVERNANCE_COLUMNS},
    "cim_standard_terms": {"standard_id", "term_code", *GOVERNANCE_COLUMNS},
    "cim_metric_mappings": {
        "source_key",
        "source_id",
        "metric_id",
        "standard_id",
        "relation_type",
        *GOVERNANCE_COLUMNS,
    },
    "cim_lifecycle_stages": {"name", "stage_key", *GOVERNANCE_COLUMNS},
    "cim_metric_lifecycle_links": {
        "metric_id",
        "lifecycle_stage_id",
        "relevance",
        *GOVERNANCE_COLUMNS,
    },
    "cim_validation_rules": {
        "name",
        "rule_type",
        "target_registry",
        "condition",
        "severity",
        *GOVERNANCE_COLUMNS,
    },
    "cim_evidence_requirements": {
        "standard_id",
        "metric_id",
        "evidence_type",
        "requirement_level",
        *GOVERNANCE_COLUMNS,
    },
    "cim_provenance_records": {
        "entity_type",
        "entity_id",
        "activity",
        "agent",
        *GOVERNANCE_COLUMNS,
    },
    "cim_extension_metrics": {
        "metric_id",
        "proposed_standard",
        "justification",
        *GOVERNANCE_COLUMNS,
    },
}


def load_m2_migration():
    spec = importlib.util.spec_from_file_location("cim_m2_migration", M2_FILE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def sqlite_engine():
    return create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )


def _run_upgrade(conn, migration):
    ctx = MigrationContext.configure(conn)
    with Operations.context(ctx):
        migration.upgrade()


def _run_downgrade(conn, migration):
    ctx = MigrationContext.configure(conn)
    with Operations.context(ctx):
        migration.downgrade()


def test_migration_module_is_reversible():
    migration = load_m2_migration()
    assert migration.revision == M2_REVISION
    assert migration.down_revision == "a7708d6bee50"
    assert callable(migration.upgrade)
    assert callable(migration.downgrade)
    assert M2_FILE.exists()


def test_upgrade_creates_all_cim_tables(sqlite_engine):
    migration = load_m2_migration()

    with sqlite_engine.begin() as conn:
        _run_upgrade(conn, migration)

        insp = inspect(conn)
        tables = set(insp.get_table_names())
        for table in CIM_REGISTRY_TABLES:
            assert table in tables, f"missing table after upgrade: {table}"

        for table, required in REQUIRED_COLUMNS.items():
            cols = {c["name"] for c in insp.get_columns(table)}
            missing = required - cols
            assert not missing, f"{table} missing columns: {missing}"

        _run_downgrade(conn, migration)

        insp_after = inspect(conn)
        remaining = set(insp_after.get_table_names()) & set(CIM_REGISTRY_TABLES)
        assert remaining == set(), f"tables remained after downgrade: {remaining}"


def test_uniqueness_constraints(sqlite_engine):
    migration = load_m2_migration()

    with sqlite_engine.begin() as conn:
        _run_upgrade(conn, migration)

    Session = sessionmaker(bind=sqlite_engine, future=True)
    with Session() as session:
        session.add(CimQuantityKind(name="Energy"))
        session.commit()

        with pytest.raises(IntegrityError):
            session.add(CimQuantityKind(name="Energy"))
            session.commit()
        session.rollback()

        qk = session.query(CimQuantityKind).filter_by(name="Energy").one()
        session.add(
            CimUnit(symbol="kWh", name="kilowatt-hour", quantity_kind_id=qk.id)
        )
        session.commit()
        with pytest.raises(IntegrityError):
            session.add(
                CimUnit(
                    symbol="kWh",
                    name="kilowatt-hour dup",
                    quantity_kind_id=qk.id,
                )
            )
            session.commit()
        session.rollback()

        session.add(
            CimMetricDefinition(
                namespace="gd.energy.consumption.total_kwh",
                status="candidate",
                review_status="under_review",
            )
        )
        session.commit()
        with pytest.raises(IntegrityError):
            session.add(
                CimMetricDefinition(namespace="gd.energy.consumption.total_kwh")
            )
            session.commit()
        session.rollback()

        session.add(CimSource(name="file_upload", type="file"))
        session.commit()
        with pytest.raises(IntegrityError):
            session.add(CimSource(name="file_upload", type="file"))
            session.commit()
        session.rollback()

        session.add(
            CimLifecycleStage(name="Operation", stage_key="operation", sequence=5)
        )
        session.commit()
        with pytest.raises(IntegrityError):
            session.add(
                CimLifecycleStage(name="Operation", stage_key="operation-dup")
            )
            session.commit()
        session.rollback()

    with sqlite_engine.begin() as conn:
        _run_downgrade(conn, migration)


def test_multi_lifecycle_and_multi_standard_mapping_support(sqlite_engine):
    """Schema supports multiple lifecycle stages and standard links per metric."""
    migration = load_m2_migration()

    with sqlite_engine.begin() as conn:
        _run_upgrade(conn, migration)

    Session = sessionmaker(bind=sqlite_engine, future=True)
    with Session() as session:
        metric = CimMetricDefinition(
            namespace="gd.energy.kpi.pue",
            status="approved",
            review_status="approved",
            confidence_score=0.95,
        )
        stage_op = CimLifecycleStage(
            name="Operation", stage_key="operation", sequence=5
        )
        stage_rep = CimLifecycleStage(
            name="Reporting", stage_key="reporting", sequence=8
        )
        std_a = CimStandard(
            code="TGG-PUE", name="The Green Grid PUE", standard_version="1"
        )
        std_b = CimStandard(
            code="ISO-50001", name="ISO 50001", standard_version="2018"
        )
        src = CimSource(name="partner_json", type="file")
        session.add_all([metric, stage_op, stage_rep, std_a, std_b, src])
        session.flush()

        session.add_all(
            [
                CimMetricLifecycleLink(
                    metric_id=metric.id,
                    lifecycle_stage_id=stage_op.id,
                    relevance="primary",
                ),
                CimMetricLifecycleLink(
                    metric_id=metric.id,
                    lifecycle_stage_id=stage_rep.id,
                    relevance="secondary",
                ),
                CimMetricMapping(
                    source_key="PUE",
                    source_id=src.id,
                    metric_id=metric.id,
                    standard_id=std_a.id,
                    relation_type="exactMatch",
                    status="approved",
                    review_status="approved",
                    confidence_score=0.99,
                ),
                CimMetricMapping(
                    source_key="power_usage_effectiveness",
                    source_id=src.id,
                    metric_id=metric.id,
                    standard_id=std_b.id,
                    relation_type="closeMatch",
                    status="candidate",
                    review_status="under_review",
                    confidence_score=0.7,
                ),
            ]
        )
        session.commit()

        links = (
            session.query(CimMetricLifecycleLink)
            .filter_by(metric_id=metric.id)
            .all()
        )
        assert len(links) == 2
        maps = session.query(CimMetricMapping).filter_by(metric_id=metric.id).all()
        assert len(maps) == 2
        assert {m.standard_id for m in maps} == {std_a.id, std_b.id}

    with sqlite_engine.begin() as conn:
        _run_downgrade(conn, migration)


def test_orm_metadata_includes_cim_tables():
    import cloud_metrics.models.cim_registry  # noqa: F401

    names = set(Base.metadata.tables.keys())
    for table in CIM_REGISTRY_TABLES:
        assert table in names


def test_legacy_tables_not_removed_by_milestone2_models():
    import cloud_metrics.models  # noqa: F401

    names = set(Base.metadata.tables.keys())
    for legacy in (
        "metric_definitions",
        "units",
        "quantity_kinds",
        "sources",
        "assets",
        "cim_mappings",
        "provenance_records",
        "standards",
    ):
        assert legacy in names
