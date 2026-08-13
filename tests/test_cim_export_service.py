"""Milestone 15: CIM export / interoperability tests."""

from __future__ import annotations

import csv
import importlib.util
import io
from pathlib import Path

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from cloud_metrics.models.cim_registry import CimMetricDefinition
from cloud_metrics.registry.export import (
    DcatExportRequest,
    WorkflowRunExportRequest,
    get_export_service,
)
from cloud_metrics.registry.extension import ExtensionRegistryService
from cloud_metrics.registry.kpi import get_kpi_calculation_service
from cloud_metrics.registry.provenance import ProvenanceRegistryService
from cloud_metrics.registry.seed import seed_all


M2_FILE = (
    Path(__file__).resolve().parents[1]
    / "migrations"
    / "versions"
    / "c2f8a1b9e047_add_cim_registry_tables.py"
)


def _load_m2():
    spec = importlib.util.spec_from_file_location("cim_m2_migration_m15", M2_FILE)
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


def _csv_rows(text: str) -> list[dict]:
    return list(csv.DictReader(io.StringIO(text)))


def test_json_metric_export(cim_session):
    svc = get_export_service(cim_session)
    payload = svc.export_json()
    assert payload["format"] == "json"
    metrics = payload["metric_definitions"]
    namespaces = {m["namespace"] for m in metrics}
    assert "cim:energy.efficiency.pue" in namespaces
    pue = next(m for m in metrics if m["namespace"] == "cim:energy.efficiency.pue")
    assert pue["status"] == "approved"
    assert pue["label"]
    assert "metric_mappings" in payload
    assert "standards_mappings" in payload
    assert "lifecycle_mappings" in payload
    assert "evidence_requirements" in payload
    assert "provenance_records" in payload
    assert "extension_candidates" in payload
    assert "kpi_results" in payload


def test_json_export_includes_kpi_results_when_provided(cim_session):
    kpi = get_kpi_calculation_service(cim_session)
    result = kpi.calculate_pue(
        {"name": "total_facility_energy", "value": 1200, "unit": "kWh"},
        {"name": "it_equipment_energy", "value": 800, "unit": "kWh"},
        aggregation_period="monthly",
        boundary="facility",
    )
    svc = get_export_service(cim_session)
    payload = svc.export_json(kpi_results=[result.to_dict()])
    assert payload["kpi_results"]
    assert payload["kpi_results"][0]["kpi_namespace"] == "cim:energy.efficiency.pue"
    assert payload["kpi_results"][0]["value"] == pytest.approx(1.5)


def test_csv_mapping_export(cim_session):
    svc = get_export_service(cim_session)
    text = svc.export_mapping_registry_csv()
    rows = _csv_rows(text)
    assert rows
    header = set(rows[0].keys())
    assert "relation_type" in header
    assert "review_status" in header
    assert "source_key" in header
    assert "cim_namespace" in header
    assert any(r["relation_type"] for r in rows)


def test_standards_crosswalk_export(cim_session):
    svc = get_export_service(cim_session)
    payload = svc.export_standards_crosswalk()
    mappings = payload["mappings"]
    assert mappings
    pue_exact = [
        m
        for m in mappings
        if m["cim_namespace"] == "cim:energy.efficiency.pue"
        and m["relation_type"] == "exactMatch"
    ]
    assert pue_exact
    assert {m["standard"] for m in pue_exact} >= {"ISO-IEC-30134", "EN-50600"}
    for row in mappings:
        assert "relation_type" in row
        assert "review_status" in row
        assert "cim_namespace" in row
        assert "standard" in row
        assert "confidence_score" in row
        assert "notes" in row
    csv_text = svc.export_standards_crosswalk_csv()
    csv_rows = _csv_rows(csv_text)
    assert any(r["relation_type"] == "exactMatch" for r in csv_rows)


def test_jsonld_export_contains_expected_fields(cim_session):
    svc = get_export_service(cim_session)
    doc = svc.export_jsonld("cim:energy.efficiency.pue")
    assert doc.get("@context")
    assert doc.get("identifier") == "cim:energy.efficiency.pue"
    assert doc.get("name")
    assert doc.get("description")
    assert doc.get("unitCode") == "ratio"
    assert doc.get("quantityKind") == "Ratio"
    mappings = doc.get("standardsMappings") or []
    assert mappings
    assert any(m.get("relationType") == "exactMatch" for m in mappings)
    assert "provenance" in doc
    assert doc.get("status") == "approved"


def test_rocrate_style_workflow_export_contains_energy_carbon_provenance(cim_session):
    prov = ProvenanceRegistryService(session=cim_session)
    metric = (
        cim_session.query(CimMetricDefinition)
        .filter_by(namespace="cim:workflow.energy.per_run")
        .one()
    )
    prov.record_activity(
        entity_type="workflow_run",
        entity_id=metric.id,
        activity="workflow_energy_attribution",
        agent="export_test",
        inputs={"workflow_id": "wf-204", "run_id": "run-2026-001"},
        outputs={"energy_kwh": 0.42},
        notes="run-2026-001",
    )
    cim_session.commit()

    svc = get_export_service(cim_session)
    crate = svc.export_rocrate_style(
        WorkflowRunExportRequest(
            workflow_id="wf-204",
            workflow_run_id="run-2026-001",
            energy_per_run=0.42,
            carbon_per_run=0.11,
            duration_seconds=3600,
            source="prometheus_node_exporter",
            asset="hpc-node-07",
            input_refs=["#input/dataset"],
            output_refs=["#output/result"],
        )
    )
    assert crate["profile"] == "ro-crate-style"
    assert crate["compliance"]["full_standards_compliance"] is False
    payload = crate["cim_payload"]
    assert payload["workflow_id"] == "wf-204"
    assert payload["workflow_run_id"] == "run-2026-001"
    assert payload["workflow_energy_per_run"] == pytest.approx(0.42)
    assert payload["workflow_carbon_per_run"] == pytest.approx(0.11)
    assert payload["provenance_records"]
    graph_ids = {item.get("@id") for item in crate["@graph"]}
    assert "ro-crate-metadata.json" in graph_ids
    run = next(
        item
        for item in crate["@graph"]
        if item.get("@id") == "#workflow-run/run-2026-001"
    )
    assert run["workflow_energy_per_run"] == pytest.approx(0.42)
    assert run["workflow_carbon_per_run"] == pytest.approx(0.11)


def test_dcat_style_export_contains_catalogue_dataset_distribution(cim_session):
    svc = get_export_service(cim_session)
    doc = svc.export_dcat_style(
        DcatExportRequest(
            title="CIM reporting dataset",
            publisher="Example RI",
            access_endpoint="https://ri.example/cim",
        )
    )
    assert doc["@type"] == "dcat:Catalog"
    assert doc["dct:title"] == "CIM reporting dataset"
    assert doc["dct:publisher"]["foaf:name"] == "Example RI"
    datasets = doc["dcat:dataset"]
    assert datasets
    dataset = datasets[0]
    assert dataset["@type"] == "dcat:Dataset"
    dists = dataset["dcat:distribution"]
    assert any(d.get("@type") == "dcat:Distribution" for d in dists)
    assert doc["dcat:service"]["dcat:endpointURL"] == "https://ri.example/cim"
    assert dataset.get("dcat:theme")
    assert doc["compliance"]["full_standards_compliance"] is False


def test_evidence_readiness_export_contains_required_evidence(cim_session):
    svc = get_export_service(cim_session)
    payload = svc.export_evidence_readiness("cim:energy.efficiency.pue")
    required = payload["required_evidence"]
    assert required
    assert any(
        (r.get("requirement_level") or "").lower() in {"mandatory", "required"}
        for r in required
    )
    assert payload["reportable_metric"] == "cim:energy.efficiency.pue"
    assert payload["readiness_status"] in {
        "declared",
        "incomplete",
        "ready",
        "not_applicable",
    }
    csv_text = svc.export_evidence_readiness_csv()
    rows = _csv_rows(csv_text)
    assert any(r["reportable_metric"] == "cim:energy.efficiency.pue" for r in rows)


def test_provenance_export_contains_expected_event_chain(cim_session):
    prov = ProvenanceRegistryService(session=cim_session)
    metric = (
        cim_session.query(CimMetricDefinition)
        .filter_by(namespace="cim:energy.efficiency.pue")
        .one()
    )
    prov.record_activity(
        entity_type="kpi_calculation",
        entity_id=metric.id,
        activity="ingestion",
        agent="test_agent",
        inputs={"sample": 1},
        outputs={"accepted": True},
    )
    prov.record_activity(
        entity_type="kpi_calculation",
        entity_id=metric.id,
        activity="kpi_calculation",
        agent="kpi_calculation_service",
        inputs={"facility": 1200, "it": 800},
        outputs={"value": 1.5},
        notes="PUE",
    )
    cim_session.commit()

    svc = get_export_service(cim_session)
    payload = svc.export_provenance(
        entity_type="kpi_calculation", entity_id=metric.id
    )
    records = payload["records"]
    activities = [r["activity"] for r in records]
    assert "ingestion" in activities
    assert "kpi_calculation" in activities
    for rec in records:
        assert rec["entity_type"] == "kpi_calculation"
        assert rec["entity_id"] == metric.id
        assert rec["agent"]
        assert rec["timestamp"]
        assert "inputs" in rec
        assert "outputs" in rec
        assert "status" in rec
        assert "notes" in rec


def test_exports_do_not_mark_candidate_metrics_approved(cim_session):
    candidate = CimMetricDefinition(
        namespace="cim:extension.custom_green_score",
        label="Custom green score",
        description="Research candidate metric",
        domain="extension",
        metric_type="extension",
        status="candidate",
        review_status="under_review",
        version=1,
        created_by="export_test",
    )
    cim_session.add(candidate)
    cim_session.flush()
    ext = ExtensionRegistryService(session=cim_session)
    ext.propose_from_raw("custom_green_score", justification="research only")
    cim_session.commit()

    svc = get_export_service(cim_session)
    json_payload = svc.export_json()
    cand = next(
        m
        for m in json_payload["metric_definitions"]
        if m["namespace"] == "cim:extension.custom_green_score"
    )
    assert cand["status"] == "candidate"
    assert cand["status"] != "approved"
    assert cand["review_status"] != "approved"

    jsonld = svc.export_jsonld("cim:extension.custom_green_score")
    assert jsonld["status"] == "candidate"
    assert jsonld["reviewStatus"] == "under_review"
    mappings = jsonld.get("standardsMappings") or []
    assert mappings == []

    ext_csv = _csv_rows(svc.export_extension_candidate_csv())
    assert ext_csv
    matched = [
        row
        for row in ext_csv
        if row["metric_namespace"] == "cim:extension.custom_green_score"
        or row.get("raw_metric_name") == "custom_green_score"
    ]
    assert matched
    for row in matched:
        assert row["status"] != "approved"
        assert row["review_status"] != "approved"


def test_csv_metric_catalogue_and_extension_datasets(cim_session):
    svc = get_export_service(cim_session)
    metrics = _csv_rows(svc.export_csv("metrics"))
    assert any(r["namespace"] == "cim:energy.efficiency.pue" for r in metrics)
    assert "status" in metrics[0]
    assert "review_status" in metrics[0]
    # unknown dataset
    with pytest.raises(ValueError):
        svc.export_csv("not-a-dataset")
