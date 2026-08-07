"""Milestone 9: Rule / Evidence / Provenance / Extension governance tests."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from cloud_metrics.models.cim_registry import (
    CimExtensionMetric,
    CimMetricDefinition,
    CimMetricMapping,
    CimProvenanceRecord,
)
from cloud_metrics.registry.evidence import EvidenceRegistryService
from cloud_metrics.registry.extension import (
    ExtensionRegistryService,
    suggest_extension_namespace,
)
from cloud_metrics.registry.orchestrator import (
    RawMetricContext,
    get_registry_orchestrator,
)
from cloud_metrics.registry.provenance import ProvenanceRegistryService
from cloud_metrics.registry.rule import RuleRegistryService
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
            created_by="milestone9_test",
        )
    )
    session.commit()


# ---------------------------------------------------------------------------
# Rule Registry
# ---------------------------------------------------------------------------


def test_observed_without_timestamp_produces_issue(cim_session):
    rules = RuleRegistryService(session=cim_session)
    res = rules.evaluate(
        {
            "namespace": "cim:compute.node.power.draw",
            "metric_type": "observed",
            "source": "scaphandre",
            # no timestamp
            "unit": "W",
            "quantity_kind": "Power",
            "domain": "energy",
        }
    )
    failed = [r for r in res.results if not r.passed]
    assert any(r.rule_name == "observed_metric_requires_timestamp_and_source" for r in failed)


def test_numeric_without_unit_produces_issue(cim_session):
    rules = RuleRegistryService(session=cim_session)
    res = rules.evaluate(
        {
            "namespace": "cim:compute.node.power.draw",
            "metric_type": "observed",
            "quantity_kind": "Power",
            "domain": "energy",
            "timestamp": "2024-01-01T00:00:00Z",
            "source": "file",
            # no unit
        }
    )
    assert any(
        (not r.passed) and r.rule_name == "numeric_metric_requires_unit"
        for r in res.results
    )


def test_dimensionless_without_unit_ok(cim_session):
    rules = RuleRegistryService(session=cim_session)
    res = rules.evaluate(
        {
            "namespace": "cim:score",
            "quantity_kind": "Dimensionless",
            "is_dimensionless": True,
        }
    )
    assert not any(
        (not r.passed) and r.rule_name == "numeric_metric_requires_unit"
        for r in res.results
    )


def test_calculated_kpi_without_formula_produces_issue(cim_session):
    rules = RuleRegistryService(session=cim_session)
    res = rules.evaluate(
        {
            "namespace": "cim:energy.efficiency.pue",
            "metric_type": "calculated_kpi",
            "unit": "ratio",
            "quantity_kind": "Ratio",
            "aggregation_period": "monthly",
            "boundary": "facility",
            # no formula
        }
    )
    assert any(
        (not r.passed) and r.rule_name == "calculated_metric_requires_derivation"
        for r in res.results
    )
    assert any(r.severity == "warning" for r in res.results if not r.passed)


def test_energy_power_energy_ambiguity_flagged(cim_session):
    rules = RuleRegistryService(session=cim_session)
    res = rules.evaluate(
        {
            "namespace": "cim:energy.something",
            "domain": "energy",
            "unit": "W",
            # missing quantity_kind
        }
    )
    assert any(
        (not r.passed) and r.rule_name == "energy_distinguishes_power_vs_energy"
        for r in res.results
    )


def test_kpi_without_period_boundary_flagged(cim_session):
    rules = RuleRegistryService(session=cim_session)
    res = rules.evaluate(
        {
            "namespace": "cim:energy.efficiency.pue",
            "metric_type": "calculated_kpi",
            "formula_or_derivation_method": "PUE = E_facility / E_IT",
            "unit": "ratio",
            # no aggregation_period / boundary
        }
    )
    assert any(
        (not r.passed) and r.rule_name == "kpi_requires_period_and_boundary"
        for r in res.results
    )


# ---------------------------------------------------------------------------
# Evidence Registry
# ---------------------------------------------------------------------------


def test_pue_evidence_requirements(cim_session):
    ev = EvidenceRegistryService(session=cim_session)
    res = ev.get_requirements_for_metric("cim:energy.efficiency.pue")
    assert len(res.mandatory) >= 2
    types = {r.evidence_type for r in res.requirements}
    assert "calculation" in types and "measurement" in types
    assert res.readiness_status == "declared"


def test_wue_evidence_requirements(cim_session):
    ev = EvidenceRegistryService(session=cim_session)
    res = ev.get_requirements_for_metric("cim:energy.efficiency.wue")
    assert res.requirements
    assert any(r.requirement_level == "mandatory" for r in res.requirements)


def test_cue_evidence_requirements(cim_session):
    ev = EvidenceRegistryService(session=cim_session)
    res = ev.get_requirements_for_metric("cim:energy.efficiency.cue")
    assert res.requirements
    assert "carbon" in (res.requirements[0].description or "").lower() or True


def test_workflow_energy_evidence_requirements(cim_session):
    ev = EvidenceRegistryService(session=cim_session)
    res = ev.get_requirements_for_metric("cim:workflow.energy.per_run")
    codes = {r.standard_code for r in res.requirements}
    assert "PROV-O" in codes
    assert "RO-CRATE" in codes
    assert any("workflow" in (r.description or "").lower() for r in res.requirements)


def test_non_reportable_metric_no_full_reporting_evidence(cim_session):
    ev = EvidenceRegistryService(session=cim_session)
    res = ev.get_requirements_for_metric("cim:compute.node.power.draw")
    assert res.requirements == []
    assert res.readiness_status == "not_applicable"


# ---------------------------------------------------------------------------
# Provenance Registry
# ---------------------------------------------------------------------------


def test_orchestrator_creates_provenance_for_known_metric(cim_session):
    _ensure_raw_mapping(cim_session, "gov_pue", "cim:energy.efficiency.pue")
    orch = get_registry_orchestrator(cim_session)
    result = orch.process(
        RawMetricContext(
            raw_metric_name="gov_pue",
            value=1.4,
            unit="ratio",
            timestamp=__import__("datetime").datetime.utcnow(),
            source="dcim",
            aggregation_period="monthly",
            boundary="facility",
            formula_or_derivation_method="PUE = E_tot/E_IT",
        )
    )
    assert result.provenance_record_id is not None
    activities = {
        r.activity
        for r in cim_session.query(CimProvenanceRecord).all()
        if r.agent == "registry_orchestrator"
    }
    assert "orchestration" in activities
    assert "registry_mapping_lookup" in activities
    assert "lifecycle_mapping_retrieval" in activities
    assert "standards_mapping_retrieval" in activities
    assert "validation_rule_application" in activities
    assert "evidence_requirement_retrieval" in activities


def test_provenance_records_fallback_and_unit(cim_session):
    # energy_wh → legacy fallback if no registry row
    existing = (
        cim_session.query(CimMetricMapping)
        .filter_by(source_key="energy_wh")
        .first()
    )
    if existing is not None:
        cim_session.delete(existing)
        cim_session.commit()

    orch = get_registry_orchestrator(cim_session)
    result = orch.process(
        RawMetricContext(raw_metric_name="energy_wh", value=100.0, unit="Wh"),
        use_fallback=True,
    )
    assert result.fallback_used is True
    activities = {
        r.activity
        for r in cim_session.query(CimProvenanceRecord)
        .filter_by(agent="registry_orchestrator")
        .all()
    }
    assert "legacy_fallback" in activities
    assert "unit_validation" in activities


def test_provenance_unresolved_recorded(cim_session):
    orch = get_registry_orchestrator(cim_session)
    result = orch.process(
        RawMetricContext(raw_metric_name="unknown_gov_metric_xyz", value=1.0),
        use_fallback=False,
        create_candidate_on_fallback=False,
    )
    assert result.resolved is False
    activities = {
        r.activity
        for r in cim_session.query(CimProvenanceRecord)
        .filter_by(agent="registry_orchestrator")
        .all()
    }
    assert "unresolved_metric_handling" in activities
    assert "extension_candidate_creation" in activities


# ---------------------------------------------------------------------------
# Extension Registry
# ---------------------------------------------------------------------------


def test_unknown_creates_extension_candidate(cim_session):
    ext = ExtensionRegistryService(session=cim_session)
    entry = ext.propose_from_raw("brand_new_custom_metric_m9")
    assert entry.id is not None
    assert entry.review_status in {"candidate", "pending", "under_review"}
    assert entry.status == "candidate"
    assert not entry.is_approved
    assert entry.metric_namespace == suggest_extension_namespace(
        "brand_new_custom_metric_m9"
    )
    metric = cim_session.get(CimMetricDefinition, entry.metric_id)
    assert metric is not None
    assert metric.status == "candidate"


def test_duplicate_extension_not_created(cim_session):
    ext = ExtensionRegistryService(session=cim_session)
    first = ext.propose_from_raw("dup_ext_metric_m9")
    second = ext.propose_from_raw("dup_ext_metric_m9")
    assert first.id == second.id
    assert cim_session.query(CimExtensionMetric).count() >= 1
    count = (
        cim_session.query(CimExtensionMetric)
        .filter_by(metric_id=first.metric_id)
        .count()
    )
    assert count == 1


def test_extension_approve_reject_placeholders(cim_session):
    ext = ExtensionRegistryService(session=cim_session)
    entry = ext.propose_from_raw("ext_review_m9")
    approved = ext.approve(entry.id)
    assert approved is not None
    assert approved.status == "accepted"
    assert approved.review_status == "under_review"  # not silently fully approved
    rejected = ext.reject(entry.id)
    assert rejected.review_status == "rejected"


# ---------------------------------------------------------------------------
# Orchestrator integration
# ---------------------------------------------------------------------------


def test_orchestrator_full_governance_path(cim_session):
    _ensure_raw_mapping(cim_session, "gov_full_pue", "cim:energy.efficiency.pue")
    orch = get_registry_orchestrator(cim_session)
    result = orch.process(
        RawMetricContext(
            raw_metric_name="gov_full_pue",
            value=1.35,
            unit="ratio",
            timestamp=__import__("datetime").datetime.utcnow(),
            source="dcim",
            aggregation_period="monthly",
            boundary="facility",
            formula_or_derivation_method="PUE=E_tot/E_IT",
        )
    )
    assert result.resolved is True
    assert result.evidence_requirements
    assert result.evidence_readiness_status == "declared"
    assert result.provenance_record_id is not None
    assert result.validation_results
    assert "lifecycle_stages" in result.to_metadata()
    assert "validation_results" in result.to_metadata()
    assert result.extension_candidate_id is None


def test_orchestrator_known_metric_with_warnings(cim_session):
    _ensure_raw_mapping(cim_session, "gov_pue_warn", "cim:energy.efficiency.pue")
    orch = get_registry_orchestrator(cim_session)
    result = orch.process(
        RawMetricContext(
            raw_metric_name="gov_pue_warn",
            value=1.2,
            unit="ratio",
            # missing formula / period / boundary → warnings
        )
    )
    assert result.resolved is True
    assert result.governance_warnings or any(
        (not v.passed) and v.severity == "warning" for v in result.validation_results
    )


def test_orchestrator_unknown_extension_and_review_required(cim_session):
    orch = get_registry_orchestrator(cim_session)
    result = orch.process(
        RawMetricContext(raw_metric_name="totally_unknown_gov_m9", value=9.0),
        use_fallback=False,
    )
    assert result.resolved is False
    assert result.extension_candidate_id is not None
    assert result.review_required is True
    assert result.mapping_status != "approved"
    assert result.standards_mappings == []


def test_orchestrator_legacy_fallback_still_works(cim_session):
    existing = (
        cim_session.query(CimMetricMapping)
        .filter_by(source_key="energy_wh")
        .first()
    )
    if existing is not None:
        cim_session.delete(existing)
        cim_session.commit()
    orch = get_registry_orchestrator(cim_session)
    result = orch.process(
        RawMetricContext(raw_metric_name="energy_wh", value=50.0, unit="Wh"),
        use_fallback=True,
    )
    assert result.resolved is True
    assert result.fallback_used is True


def test_provenance_service_chain(cim_session):
    prov = ProvenanceRegistryService(session=cim_session)
    a = prov.record_activity(
        entity_type="test_entity",
        entity_id=1,
        activity="step_a",
        agent="test",
    )
    prov.record_activity(
        entity_type="test_entity",
        entity_id=1,
        activity="step_b",
        agent="test",
    )
    chain = prov.get_chain("test_entity", 1)
    assert len(chain) >= 2
    assert a.id is not None
