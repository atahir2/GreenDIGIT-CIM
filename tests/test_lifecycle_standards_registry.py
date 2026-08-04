"""Milestone 8: Lifecycle + Standards registry integration tests."""

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
from cloud_metrics.registry.lifecycle import LifecycleRegistryService
from cloud_metrics.registry.orchestrator import (
    RawMetricContext,
    get_registry_orchestrator,
)
from cloud_metrics.registry.seed import seed_all
from cloud_metrics.registry.standards import StandardsRegistryService


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


def _ensure_raw_mapping(session, raw_key: str, namespace: str) -> None:
    metric = session.query(CimMetricDefinition).filter_by(namespace=namespace).one()
    existing = (
        session.query(CimMetricMapping)
        .filter_by(source_key=raw_key, source_id=None)
        .first()
    )
    if existing:
        return
    session.add(
        CimMetricMapping(
            source_key=raw_key,
            source_id=None,
            metric_id=metric.id,
            relation_type="exactMatch",
            origin="test",
            status="approved",
            review_status="approved",
            confidence_score=1.0,
            version=1,
            created_by="milestone8_test",
        )
    )
    session.commit()


# ---------------------------------------------------------------------------
# Lifecycle service
# ---------------------------------------------------------------------------


def test_pue_lifecycle_stages(cim_session):
    life = LifecycleRegistryService(session=cim_session)
    res = life.get_links_for_metric("cim:energy.efficiency.pue")
    assert set(res.stages) == {"operation", "reporting", "continuous_improvement"}
    assert "required" in res.importance
    assert "recommended" in res.importance


def test_node_power_lifecycle_stages(cim_session):
    life = LifecycleRegistryService(session=cim_session)
    res = life.get_links_for_metric("cim:compute.node.power.draw")
    assert "operation" in res.stages
    assert "optimisation" in res.stages
    assert "reproducibility" in res.stages
    assert "reporting" in res.stages
    # reporting is conditional
    reporting = [lnk for lnk in res.links if lnk.stage_key == "reporting"]
    assert reporting and reporting[0].importance == "conditional"


def test_carbon_lifecycle_operation_reporting(cim_session):
    life = LifecycleRegistryService(session=cim_session)
    res = life.get_links_for_metric("cim:carbon.emission.operational")
    assert set(res.stages) == {"operation", "reporting"}


def test_lifecycle_does_not_invent_stages(cim_session):
    life = LifecycleRegistryService(session=cim_session)
    res = life.get_links_for_metric("cim:compute.cpu.utilisation")
    assert res.stages == []
    assert res.message == "no lifecycle links seeded"


# ---------------------------------------------------------------------------
# Standards service
# ---------------------------------------------------------------------------


def test_pue_exact_match_iso_en(cim_session):
    std = StandardsRegistryService(session=cim_session)
    res = std.get_mappings_for_metric("cim:energy.efficiency.pue")
    codes = {m.standard_code: m.relation_type for m in res.mappings}
    assert codes.get("ISO-IEC-30134") == "exactMatch"
    assert codes.get("EN-50600") == "exactMatch"
    assert res.no_direct_standard_match is False


def test_node_power_input_to_kpi_not_false_exact(cim_session):
    std = StandardsRegistryService(session=cim_session)
    res = std.get_mappings_for_metric("cim:compute.node.power.draw")
    relations = {m.standard_code: m.relation_type for m in res.mappings}
    assert relations.get("ISO-IEC-30134") == "inputToKPI"
    assert relations.get("EN-50600") == "inputToKPI"
    assert relations.get("QUDT") == "contextualMatch"
    assert relations.get("SOSA-SSN") == "contextualMatch"
    assert relations.get("SAREF") == "closeMatch"
    assert "exactMatch" not in res.relation_types
    assert res.no_direct_standard_match is True


def test_gpu_power_contextual_and_ocp(cim_session):
    std = StandardsRegistryService(session=cim_session)
    res = std.get_mappings_for_metric("cim:compute.gpu.power.average")
    codes = {m.standard_code: m.relation_type for m in res.mappings}
    assert codes.get("QUDT") == "contextualMatch"
    assert codes.get("SOSA-SSN") == "contextualMatch"
    assert codes.get("SAREF") == "closeMatch"
    assert codes.get("OCP") == "contextualMatch"
    assert "exactMatch" not in res.relation_types


def test_workflow_energy_repro_standards_no_iso_exact(cim_session):
    life = LifecycleRegistryService(session=cim_session)
    life_res = life.get_links_for_metric("cim:workflow.energy.per_run")
    assert "reproducibility" in life_res.stages
    assert "operation" in life_res.stages
    assert "reporting" in life_res.stages

    std = StandardsRegistryService(session=cim_session)
    res = std.get_mappings_for_metric("cim:workflow.energy.per_run")
    codes = {m.standard_code: m.relation_type for m in res.mappings}
    assert codes.get("PROV-O") == "contextualMatch"
    assert codes.get("RO-CRATE") == "contextualMatch"
    assert codes.get("SCHEMA-ORG") == "contextualMatch"
    assert codes.get("QUDT") == "contextualMatch"
    assert codes.get("ISO-IEC-30134") is None
    assert codes.get("EN-50600") is None
    assert "exactMatch" not in res.relation_types
    assert res.no_direct_standard_match is True


def test_candidate_metric_no_approved_standards(cim_session):
    # Create a candidate metric definition
    metric = CimMetricDefinition(
        namespace="cim:extension.unknown.candidate_m8",
        label="Candidate",
        status="candidate",
        review_status="under_review",
        version=1,
        created_by="milestone8_test",
    )
    cim_session.add(metric)
    cim_session.flush()
    # Even if an approved standards mapping row exists for the candidate metric,
    # the service must suppress it.
    from cloud_metrics.models.cim_registry import CimStandard

    iso = cim_session.query(CimStandard).filter_by(code="ISO-IEC-30134").one()
    cim_session.add(
        CimMetricMapping(
            source_key="std:ISO-IEC-30134:bad:cim:extension.unknown.candidate_m8",
            metric_id=metric.id,
            standard_id=iso.id,
            relation_type="exactMatch",
            status="approved",
            review_status="approved",
            origin="test",
            version=1,
            created_by="milestone8_test",
            confidence_score=1.0,
        )
    )
    cim_session.commit()

    std = StandardsRegistryService(session=cim_session)
    res = std.get_mappings_for_metric(metric.namespace)
    assert res.mappings == []
    assert res.no_direct_standard_match is True


# ---------------------------------------------------------------------------
# Orchestrator enrichment
# ---------------------------------------------------------------------------


def test_orchestrator_includes_lifecycle_and_standards(cim_session):
    _ensure_raw_mapping(cim_session, "orch_pue_m8", "cim:energy.efficiency.pue")
    orch = get_registry_orchestrator(cim_session)
    result = orch.process(RawMetricContext(raw_metric_name="orch_pue_m8", value=1.4))
    assert result.resolved is True
    assert set(result.lifecycle_stages) == {
        "operation",
        "reporting",
        "continuous_improvement",
    }
    assert result.lifecycle_usage_purposes
    assert result.lifecycle_importance
    assert result.lifecycle_review_status
    codes = {m.standard_code: m.relation_type for m in result.standards_mappings}
    assert codes.get("ISO-IEC-30134") == "exactMatch"
    assert codes.get("EN-50600") == "exactMatch"
    assert result.no_direct_standard_match is False
    meta = result.to_metadata()
    assert "lifecycle_stages" in meta
    assert "standards_mappings" in meta


def test_orchestrator_node_power_lifecycle_and_standards(cim_session):
    _ensure_raw_mapping(cim_session, "orch_node_pwr", "cim:compute.node.power.draw")
    orch = get_registry_orchestrator(cim_session)
    result = orch.process(
        RawMetricContext(raw_metric_name="orch_node_pwr", value=350.0, unit="W")
    )
    assert "operation" in result.lifecycle_stages
    assert "optimisation" in result.lifecycle_stages
    assert "reproducibility" in result.lifecycle_stages
    assert "exactMatch" not in result.standards_relation_types
    assert "inputToKPI" in result.standards_relation_types
    assert result.no_direct_standard_match is True


def test_orchestrator_unknown_no_approved_standards(cim_session):
    orch = get_registry_orchestrator(cim_session)
    result = orch.process(
        RawMetricContext(raw_metric_name="totally_unknown_m8_xyz", value=1.0),
        use_fallback=False,
        create_candidate_on_fallback=False,
    )
    assert result.resolved is False
    assert result.standards_mappings == []
    assert result.no_direct_standard_match is True
    assert result.lifecycle_stages == []


def test_orchestrator_missing_lifecycle_does_not_break(cim_session):
    _ensure_raw_mapping(cim_session, "orch_cpu_m8", "cim:compute.cpu.utilisation")
    orch = get_registry_orchestrator(cim_session)
    result = orch.process(RawMetricContext(raw_metric_name="orch_cpu_m8", value=0.5))
    assert result.resolved is True
    assert result.lifecycle_stages == []
    # Still a valid result — soft enrichment
    assert result.errors == []
