"""Milestone 10: End-to-end registry-driven CIM demonstrator tests."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from cloud_metrics.demo.cim_demonstrator import (
    DEMO_RAW_TO_CIM,
    FIXTURE_DIR,
    SAMPLE_FILES,
    critical_rule_failures,
    ensure_demo_mappings,
    load_sample,
    load_unstructured_sample,
    prepare_pue_context,
    process_sample,
    run_all_scenarios,
    run_scenario,
    sample_to_contexts,
)
from cloud_metrics.models.cim_registry import (
    CimExtensionMetric,
    CimMetricMapping,
    CimProvenanceRecord,
)
from cloud_metrics.registry.orchestrator import RawMetricContext, get_registry_orchestrator
from cloud_metrics.registry.seed import seed_all


M2_FILE = (
    Path(__file__).resolve().parents[1]
    / "migrations"
    / "versions"
    / "c2f8a1b9e047_add_cim_registry_tables.py"
)


def _load_m2():
    spec = importlib.util.spec_from_file_location("cim_m2_migration_e2e", M2_FILE)
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
    ensure_demo_mappings(session)
    yield session

    session.close()
    with engine.begin() as conn:
        ctx = MigrationContext.configure(conn)
        with Operations.context(ctx):
            migration.downgrade()


# ---------------------------------------------------------------------------
# Fixtures present
# ---------------------------------------------------------------------------


def test_demo_fixtures_exist():
    assert FIXTURE_DIR.is_dir()
    for name in SAMPLE_FILES.values():
        assert (FIXTURE_DIR / name).is_file()
    assert (FIXTURE_DIR / "unstructured_metrics_sample.txt").is_file()


def test_demo_raw_mappings_cover_known_samples():
    for fname in (
        "known_metrics_sample.json",
        "wrong_units_sample.json",
        "workflow_run_metrics_sample.json",
        "facility_kpi_sample.json",
    ):
        sample = load_sample(fname)
        for metric in sample["metrics"]:
            assert metric["name"] in DEMO_RAW_TO_CIM, metric["name"]


# ---------------------------------------------------------------------------
# Scenario A — known operational
# ---------------------------------------------------------------------------


def test_scenario_a_known_node_power(cim_session):
    report = run_scenario(cim_session, "A", ensure_mappings=False)
    by_name = {r.raw_metric_name: r for r in report["orchestrator_results"]}
    result = by_name["node_power_watts"]

    assert result.resolved is True
    assert result.fallback_used is False
    assert result.resolution_path == "registry"
    assert result.cim_namespace == "cim:compute.node.power.draw"
    assert result.unit_validation_status == "valid"
    assert result.expected_quantity_kind == "Power"
    assert result.canonical_unit == "W"
    assert result.source_resolution_status in {"resolved", "candidate_created"}
    assert result.source_id is not None
    assert result.asset_resolution_status in {"resolved", "candidate_created"}
    assert result.asset_id is not None
    assert "operation" in result.lifecycle_stages
    assert "optimisation" in result.lifecycle_stages
    assert "inputToKPI" in result.standards_relation_types or any(
        r in result.standards_relation_types
        for r in ("contextualMatch", "closeMatch")
    )
    assert "exactMatch" not in result.standards_relation_types
    assert not critical_rule_failures(result) or result.review_required is not None
    # No critical *silent* acceptance of bad data — known valid path
    assert result.candidate_flags.get("unit_incompatible") is not True
    assert result.provenance_record_id is not None
    assert result.provenance_log_reference


def test_scenario_a_other_known_metrics_map(cim_session):
    report = run_scenario(cim_session, "A", ensure_mappings=False)
    expected = {
        "gpu_avg_power": "cim:compute.gpu.power.average",
        "cpu_utilisation": "cim:compute.cpu.utilisation",
        "memory_used": "cim:compute.memory.usage",
        "network_ingress": "cim:network.traffic.ingress",
    }
    by_name = {r.raw_metric_name: r for r in report["orchestrator_results"]}
    for raw, ns in expected.items():
        assert by_name[raw].cim_namespace == ns
        assert by_name[raw].resolved is True
        assert by_name[raw].unit_validation_status in {"valid", "normalized"}


# ---------------------------------------------------------------------------
# Scenario B — wrong units
# ---------------------------------------------------------------------------


def test_scenario_b_wrong_unit_flagged(cim_session):
    report = run_scenario(cim_session, "B", ensure_mappings=False)
    by_name = {r.raw_metric_name: r for r in report["orchestrator_results"]}

    power = by_name["node_power_watts"]
    assert power.cim_namespace == "cim:compute.node.power.draw"
    assert power.resolved is True  # soft — mapping still succeeds
    assert power.unit_validation_status == "incompatible"
    assert power.candidate_flags.get("unit_incompatible") is True
    assert power.observed_unit == "kWh"
    assert any("incompatible" in w.lower() or "unit" in w.lower() for w in power.warnings)
    assert power.provenance_record_id is not None

    energy = by_name["energy_consumption"]
    assert energy.cim_namespace == "cim:energy.consumption.total"
    assert energy.unit_validation_status == "incompatible"

    intensity = by_name["carbon_intensity"]
    assert intensity.cim_namespace == "cim:carbon.intensity.location_based"
    assert intensity.unit_validation_status == "incompatible"

    # Governance should surface issues (warnings/errors or failed rules)
    assert (
        power.governance_warnings
        or power.governance_errors
        or power.warnings
        or any(not v.passed for v in power.validation_results)
    )


# ---------------------------------------------------------------------------
# Scenario C — workflow reproducibility
# ---------------------------------------------------------------------------


def test_scenario_c_workflow_energy(cim_session):
    report = run_scenario(cim_session, "C", ensure_mappings=False)
    by_name = {r.raw_metric_name: r for r in report["orchestrator_results"]}
    result = by_name["workflow_energy_per_run"]

    assert result.resolved is True
    assert result.cim_namespace == "cim:workflow.energy.per_run"
    assert result.unit_validation_status == "valid"
    assert result.expected_quantity_kind == "Energy"
    assert result.canonical_unit == "kWh"
    assert "reproducibility" in result.lifecycle_stages
    assert "operation" in result.lifecycle_stages

    # Workflow / run context preserved
    meta = result.original_raw_metadata
    assert meta.get("workflow_id") == "wf-204"
    assert meta.get("run_id") == "run-2026-001" or meta.get("workflow_run_id") == "run-2026-001"

    # Standards: PROV-O / RO-Crate / schema.org relevance; no false ISO/EN exactMatch
    codes = {m.standard_code: m.relation_type for m in result.standards_mappings}
    assert codes.get("ISO-IEC-30134") != "exactMatch"
    assert codes.get("EN-50600") != "exactMatch"
    assert any(
        c in codes for c in ("PROV-O", "RO-CRATE", "SCHEMA-ORG", "QUDT")
    )

    assert result.evidence_requirements
    assert any(
        e.standard_code in {"PROV-O", "RO-CRATE"} for e in result.evidence_requirements
    )
    assert result.provenance_record_id is not None


# ---------------------------------------------------------------------------
# Scenario D — facility KPI / PUE preparation
# ---------------------------------------------------------------------------


def test_scenario_d_facility_and_pue_evidence(cim_session):
    report = run_scenario(cim_session, "D", ensure_mappings=False)
    by_name = {r.raw_metric_name: r for r in report["orchestrator_results"]}

    total = by_name["total_facility_energy"]
    it_energy = by_name["it_equipment_energy"]
    assert total.cim_namespace == "cim:facility.energy.consumption.total"
    assert it_energy.cim_namespace == "cim:facility.it.energy.consumption"
    assert total.unit_validation_status == "valid"
    assert it_energy.unit_validation_status == "valid"

    assert "pue_preparation" in report
    pue = report["pue_orchestrator_result"]
    assert pue.cim_namespace == "cim:energy.efficiency.pue"
    assert pue.resolved is True
    assert pue.evidence_requirements
    assert any(e.standard_code == "ISO-IEC-30134" for e in pue.evidence_requirements)

    codes = {m.standard_code: m.relation_type for m in pue.standards_mappings}
    assert codes.get("ISO-IEC-30134") == "exactMatch"
    assert codes.get("EN-50600") == "exactMatch"
    assert report["pue_preparation"]["prepared_value"] == 1.5


def test_prepare_pue_context_ratio():
    sample = load_sample("facility_kpi_sample.json")
    ctx = prepare_pue_context(sample)
    assert ctx is not None
    assert ctx.value == 1.5
    assert ctx.unit == "ratio"
    assert ctx.aggregation_period == "monthly"
    assert ctx.boundary == "facility"


# ---------------------------------------------------------------------------
# Scenario E — unknown / extension
# ---------------------------------------------------------------------------


def test_scenario_e_extension_candidate(cim_session):
    report = run_scenario(cim_session, "E", ensure_mappings=False)
    by_name = {r.raw_metric_name: r for r in report["orchestrator_results"]}
    result = by_name["workflow_green_score"]

    assert result.resolved is False
    assert result.candidate_flags.get("metric_unresolved") is True
    assert result.fallback_used is False
    # Must not assign an approved seeded operational / performance namespace
    assert result.mapping_status not in {"approved", "active"}
    assert result.cim_namespace is None or result.cim_namespace.startswith("cim:extension.")

    assert result.extension_candidate_id is not None
    ext = cim_session.get(CimExtensionMetric, result.extension_candidate_id)
    assert ext is not None
    assert (ext.review_status or "").lower() in {
        "candidate",
        "pending",
        "under_review",
    }
    assert (ext.status or "").lower() == "candidate"
    assert result.standards_mappings == []
    assert result.no_direct_standard_match is True
    assert result.provenance_record_id is not None


def test_scenario_e_all_unknowns_create_candidates(cim_session):
    report = run_scenario(cim_session, "E", ensure_mappings=False)
    for r in report["orchestrator_results"]:
        assert r.extension_candidate_id is not None
        assert r.review_required is True


# ---------------------------------------------------------------------------
# Provenance, lifecycle, legacy fallback, full suite
# ---------------------------------------------------------------------------


def test_provenance_created_across_scenarios(cim_session):
    run_all_scenarios(cim_session)
    rows = (
        cim_session.query(CimProvenanceRecord)
        .filter_by(agent="registry_orchestrator")
        .all()
    )
    assert len(rows) >= 5
    activities = {r.activity for r in rows}
    assert "orchestration" in activities


def test_legacy_fallback_still_works(cim_session):
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
        create_candidate_on_fallback=True,
    )
    assert result.resolved is True
    assert result.fallback_used is True
    assert result.resolution_path == "legacy_fallback"
    assert result.cim_namespace == "cim:energy.consumption.total"


def test_run_all_scenarios_smoke(cim_session):
    report = run_all_scenarios(cim_session)
    assert set(report["scenarios"].keys()) == set(SAMPLE_FILES.keys())
    assert report["unstructured"] is not None
    assert "extracted" in report["unstructured"]


def test_unstructured_parser_optional_sample():
    from cloud_metrics.parsers.unstructured_parser import parse_unstructured_text

    text = load_unstructured_sample()
    extracted = parse_unstructured_text(text, datacenter="RI-site-1")
    assert extracted
    # Existing parser returns datacenter.metric keys
    assert any("cpu" in k for k in extracted)


def test_sample_to_contexts_preserves_workflow_ids():
    sample = load_sample("workflow_run_metrics_sample.json")
    contexts = sample_to_contexts(sample)
    assert contexts
    assert contexts[0].workflow_id == "wf-204"
    assert contexts[0].run_id == "run-2026-001"


def test_process_sample_direct(cim_session):
    sample = load_sample("known_metrics_sample.json")
    results = process_sample(cim_session, sample)
    assert len(results) == len(sample["metrics"])
