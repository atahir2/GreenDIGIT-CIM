"""Milestone 16C: API-based CIM integration for external organizations / RIs."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from cloud_metrics.demo.cim_demonstrator import ensure_demo_mappings
from cloud_metrics.main import app
from cloud_metrics.registry.seed import seed_all
from cloud_metrics.services.cim_api_ingest import ingest_external_payload


M2_FILE = (
    Path(__file__).resolve().parents[1]
    / "migrations"
    / "versions"
    / "c2f8a1b9e047_add_cim_registry_tables.py"
)


def _load_m2():
    spec = importlib.util.spec_from_file_location("cim_m2_migration_ms16c", M2_FILE)
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


@pytest.fixture()
def client(cim_session, monkeypatch):
    def _get_db():
        try:
            yield cim_session
        finally:
            pass

    monkeypatch.setattr(
        "cloud_metrics.api.cim_ingest_api.get_db",
        _get_db,
    )
    monkeypatch.setattr(
        "cloud_metrics.api.cim_kpi_api.get_db",
        _get_db,
    )
    return TestClient(app)


def _by_name(resp: dict) -> dict:
    return {r["raw_metric_name"]: r for r in resp.get("results") or []}


# ---------------------------------------------------------------------------
# Service-level scenarios
# ---------------------------------------------------------------------------


def test_api_scenario_a_known_operational(cim_session):
    payload = {
        "organization_id": "ri-org-a",
        "source": "prometheus_node_exporter",
        "source_type": "monitoring_system",
        "timestamp": "2026-08-07T10:15:00Z",
        "asset": {"node": "hpc-node-07", "site": "RI-site-1"},
        "source_metadata": {"job": "node_exporter"},
        "metrics": [{"name": "node_power_watts", "value": 420, "unit": "W"}],
    }
    out = ingest_external_payload(cim_session, payload)
    row = _by_name(out)["node_power_watts"]
    assert row["cim_namespace"] == "cim:compute.node.power.draw"
    assert row["resolved"] is True
    assert row.get("unit_validation_status") == "valid"
    assert row.get("provenance_record_id") or row.get("provenance_log_reference")
    assert not row.get("critical_issues")
    assert row.get("extension_candidate_id") is None


def test_api_scenario_b_wrong_unit(cim_session):
    payload = {
        "organization_id": "ri-org-b",
        "source": "prometheus_node_exporter",
        "source_type": "monitoring_system",
        "metrics": [{"name": "node_power_watts", "value": 420, "unit": "kWh"}],
    }
    out = ingest_external_payload(cim_session, payload)
    row = _by_name(out)["node_power_watts"]
    assert row["cim_namespace"] == "cim:compute.node.power.draw"
    assert (row.get("unit_validation_status") or "").lower() == "incompatible"
    assert row.get("critical_issues")
    assert row.get("accepted_as_valid") is False


def test_api_scenario_c_workflow(cim_session):
    payload = {
        "organization_id": "ri-org-c",
        "source": "workflow_energy_profiler",
        "source_type": "workflow_instrumentation",
        "workflow_id": "wf-204",
        "run_id": "run-2026-001",
        "formula_or_derivation_method": "sum_of_node_energy_over_run_window",
        "metrics": [
            {"name": "workflow_energy_per_run", "value": 0.42, "unit": "kWh"},
            {"name": "workflow_carbon_per_run", "value": 0.11, "unit": "kgCO2e"},
        ],
    }
    out = ingest_external_payload(cim_session, payload)
    by = _by_name(out)
    energy = by["workflow_energy_per_run"]
    carbon = by["workflow_carbon_per_run"]
    assert energy["cim_namespace"] == "cim:workflow.energy.per_run"
    assert carbon["cim_namespace"] == "cim:workflow.carbon.per_run"
    assert energy.get("provenance_record_id") or energy.get("provenance_log_reference")
    # No false ISO/EN exactMatch for workflow metrics
    relations = list(energy.get("standards_relation_types") or [])
    assert "exactMatch" not in relations
    assert energy.get("resolved") is True


def test_api_scenario_d_facility_kpi(cim_session):
    payload = {
        "organization_id": "ri-org-d",
        "source": "facility_bms",
        "source_type": "building_management_system",
        "aggregation_period": "monthly",
        "boundary": "facility",
        "metrics": [
            {"name": "total_facility_energy", "value": 1200, "unit": "kWh"},
            {"name": "it_equipment_energy", "value": 800, "unit": "kWh"},
            {"name": "water_usage_total", "value": 2.5, "unit": "m3"},
            {"name": "carbon_emission_operational", "value": 250, "unit": "kgCO2e"},
        ],
    }
    out = ingest_external_payload(
        cim_session, payload, options={"calculate_kpi": "pue"}
    )
    by = _by_name(out)
    assert by["total_facility_energy"]["cim_namespace"] == (
        "cim:facility.energy.consumption.total"
    )
    assert by["it_equipment_energy"]["cim_namespace"] == (
        "cim:facility.it.energy.consumption"
    )
    kpi = out.get("kpi") or {}
    assert kpi.get("calculation_status") in {
        "calculated",
        "blocked",
        "under_review",
        "invalid_unit",
        "missing_input",
    }
    if kpi.get("calculation_status") == "calculated":
        assert kpi.get("value") == pytest.approx(1.5)
        assert kpi.get("provenance_record_id")


def test_api_scenario_d_kpi_blocks_bad_unit(cim_session):
    payload = {
        "organization_id": "ri-org-d2",
        "source": "facility_bms",
        "aggregation_period": "monthly",
        "boundary": "facility",
        "metrics": [
            {"name": "total_facility_energy", "value": 1200, "unit": "W"},
            {"name": "it_equipment_energy", "value": 800, "unit": "kWh"},
        ],
    }
    out = ingest_external_payload(
        cim_session, payload, options={"calculate_kpi": "pue"}
    )
    kpi = out.get("kpi") or {}
    assert kpi.get("calculation_status") in {"invalid_unit", "blocked"}
    assert kpi.get("reportable_approved") in {False, None}


def test_api_scenario_e_unknown_extension(cim_session):
    payload = {
        "organization_id": "ri-org-e",
        "source": "research_scheduler",
        "source_type": "experimental_tooling",
        "metrics": [{"name": "workflow_green_score", "value": 0.78, "unit": "score"}],
    }
    out = ingest_external_payload(
        cim_session,
        payload,
        options={
            "use_fallback": False,
            "create_candidate_on_fallback": False,
            "create_extension_on_unresolved": True,
        },
    )
    row = _by_name(out)["workflow_green_score"]
    assert row.get("resolved") is False or row.get("cim_namespace") is None or str(
        row.get("cim_namespace") or ""
    ).startswith("cim:extension.")
    assert row.get("extension_candidate_id") is not None or (
        row.get("mapping_status") or ""
    ).lower() in {"candidate", "unresolved", "under_review"}
    # Never silently approved
    assert (row.get("mapping_status") or "").lower() not in {"approved", "active"}


# ---------------------------------------------------------------------------
# HTTP endpoints
# ---------------------------------------------------------------------------


def test_http_ingest_metrics_scenario_a(client):
    res = client.post(
        "/api/v1/cim-ingest/metrics",
        json={
            "organization_id": "ri-http-a",
            "source": "prometheus_node_exporter",
            "source_type": "monitoring_system",
            "timestamp": "2026-08-07T10:15:00Z",
            "asset": {"node": "hpc-node-07", "site": "RI-site-1"},
            "metrics": [{"name": "node_power_watts", "value": 420, "unit": "W"}],
            "options": {"ensure_demo_mappings": True},
        },
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["metrics_processed"] == 1
    row = body["results"][0]
    assert row["cim_namespace"] == "cim:compute.node.power.draw"


def test_http_ingest_scenario_helpers(client):
    for letter in ("A", "B", "C", "D", "E"):
        res = client.post(f"/api/v1/cim-ingest/scenarios/{letter}")
        assert res.status_code == 200, f"{letter}: {res.text}"
        body = res.json()
        assert body["metrics_processed"] >= 1
        assert body["organization_id"] == f"demo-scenario-{letter}"


def test_http_ingest_requires_metrics(client):
    res = client.post(
        "/api/v1/cim-ingest/metrics",
        json={"organization_id": "x", "metrics": []},
    )
    assert res.status_code == 400


def test_http_ingest_unknown_scenario(client):
    res = client.post("/api/v1/cim-ingest/scenarios/Z")
    assert res.status_code == 400
