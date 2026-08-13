"""Milestone 13: KPI Calculation Service tests (PUE / WUE / CUE)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from cloud_metrics.models.cim_registry import CimMetricDefinition, CimProvenanceRecord
from cloud_metrics.registry.kpi import (
    KPI_CUE,
    KPI_PUE,
    KPI_WUE,
    KpiCalculationService,
    KpiInput,
    get_kpi_calculation_service,
)
from cloud_metrics.registry.seed import seed_all


M2_FILE = (
    Path(__file__).resolve().parents[1]
    / "migrations"
    / "versions"
    / "c2f8a1b9e047_add_cim_registry_tables.py"
)


def _load_m2():
    spec = importlib.util.spec_from_file_location("cim_m2_migration_m13", M2_FILE)
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


def _pue_ok(svc, **extra):
    kwargs = dict(
        aggregation_period="monthly",
        boundary="facility",
    )
    kwargs.update(extra)
    return svc.calculate_pue(
        {"name": "total_facility_energy", "value": 1200, "unit": "kWh"},
        {"name": "it_equipment_energy", "value": 800, "unit": "kWh"},
        **kwargs,
    )


# ---------------------------------------------------------------------------
# PUE
# ---------------------------------------------------------------------------


def test_valid_pue_calculation(cim_session):
    svc = get_kpi_calculation_service(cim_session)
    result = _pue_ok(svc)
    assert result.calculation_status == "calculated"
    assert result.reportable_approved is True
    assert result.kpi_namespace == KPI_PUE
    assert result.value == pytest.approx(1.5)
    assert result.unit == "ratio"
    assert result.validation_status == "valid"
    assert result.aggregation_period == "monthly"
    assert result.boundary == "facility"


def test_pue_normalizes_compatible_energy_units(cim_session):
    svc = KpiCalculationService(session=cim_session)
    result = svc.calculate_pue(
        KpiInput(name="total_facility_energy", value=1_200_000, unit="Wh"),
        KpiInput(name="it_equipment_energy", value=800, unit="kWh"),
        aggregation_period="monthly",
        boundary="facility",
    )
    assert result.calculation_status == "calculated"
    assert result.value == pytest.approx(1.5)


def test_pue_blocked_by_zero_it_energy(cim_session):
    svc = get_kpi_calculation_service(cim_session)
    result = svc.calculate_pue(
        {"name": "total_facility_energy", "value": 1200, "unit": "kWh"},
        {"name": "it_equipment_energy", "value": 0, "unit": "kWh"},
        aggregation_period="monthly",
        boundary="facility",
    )
    assert result.calculation_status == "blocked"
    assert result.reportable_approved is False
    assert result.value is None
    assert any("zero" in e.lower() for e in result.errors)


def test_pue_blocked_by_incompatible_unit(cim_session):
    svc = get_kpi_calculation_service(cim_session)
    result = svc.calculate_pue(
        {"name": "total_facility_energy", "value": 1200, "unit": "W"},
        {"name": "it_equipment_energy", "value": 800, "unit": "kWh"},
        aggregation_period="monthly",
        boundary="facility",
    )
    assert result.calculation_status == "invalid_unit"
    assert result.value is None
    assert result.reportable_approved is False


def test_pue_blocked_by_missing_aggregation_period(cim_session):
    svc = get_kpi_calculation_service(cim_session)
    result = svc.calculate_pue(
        {"name": "total_facility_energy", "value": 1200, "unit": "kWh"},
        {"name": "it_equipment_energy", "value": 800, "unit": "kWh"},
        boundary="facility",
    )
    assert result.calculation_status == "blocked"
    assert any("aggregation period" in e.lower() for e in result.errors)


def test_pue_blocked_by_missing_boundary(cim_session):
    svc = get_kpi_calculation_service(cim_session)
    result = svc.calculate_pue(
        {"name": "total_facility_energy", "value": 1200, "unit": "kWh"},
        {"name": "it_equipment_energy", "value": 800, "unit": "kWh"},
        aggregation_period="monthly",
    )
    assert result.calculation_status == "blocked"
    assert any("boundary" in e.lower() for e in result.errors)


def test_pue_returns_evidence_requirements(cim_session):
    svc = get_kpi_calculation_service(cim_session)
    result = _pue_ok(svc)
    assert result.evidence_requirements
    assert any(e.standard_code == "ISO-IEC-30134" for e in result.evidence_requirements)


def test_pue_creates_provenance_record(cim_session):
    svc = get_kpi_calculation_service(cim_session)
    result = _pue_ok(svc)
    assert result.provenance_record_id is not None
    row = cim_session.get(CimProvenanceRecord, result.provenance_record_id)
    assert row is not None
    assert row.activity == "kpi_calculation"
    assert row.agent == "kpi_calculation_service"
    assert row.outputs.get("calculation_status") == "calculated"


def test_pue_blocked_still_records_provenance(cim_session):
    svc = get_kpi_calculation_service(cim_session)
    result = svc.calculate_pue(
        {"name": "total_facility_energy", "value": 1200, "unit": "W"},
        {"name": "it_equipment_energy", "value": 800, "unit": "kWh"},
        aggregation_period="monthly",
        boundary="facility",
    )
    assert result.calculation_status == "invalid_unit"
    assert result.provenance_record_id is not None


def test_pue_missing_input(cim_session):
    svc = get_kpi_calculation_service(cim_session)
    result = svc.calculate_pue(
        {"name": "total_facility_energy", "value": None, "unit": "kWh"},
        {"name": "it_equipment_energy", "value": 800, "unit": "kWh"},
        aggregation_period="monthly",
        boundary="facility",
    )
    assert result.calculation_status == "missing_input"


# ---------------------------------------------------------------------------
# WUE
# ---------------------------------------------------------------------------


def test_valid_wue_calculation(cim_session):
    svc = get_kpi_calculation_service(cim_session)
    result = svc.calculate_wue(
        {"name": "water_usage_total", "value": 2.5, "unit": "m3"},
        {"name": "it_equipment_energy", "value": 800, "unit": "kWh"},
        aggregation_period="monthly",
        boundary="site_or_facility",
    )
    assert result.calculation_status == "calculated"
    assert result.kpi_namespace == KPI_WUE
    # 2.5 m3 = 2500 L; 2500 / 800 = 3.125 L/kWh
    assert result.value == pytest.approx(3.125)
    assert result.unit == "L/kWh"
    assert result.evidence_requirements
    assert result.provenance_record_id is not None


def test_wue_blocked_by_incompatible_water_unit(cim_session):
    svc = get_kpi_calculation_service(cim_session)
    result = svc.calculate_wue(
        {"name": "water_usage_total", "value": 2.5, "unit": "kWh"},
        {"name": "it_equipment_energy", "value": 800, "unit": "kWh"},
        aggregation_period="monthly",
        boundary="facility",
    )
    assert result.calculation_status == "invalid_unit"
    assert result.value is None


# ---------------------------------------------------------------------------
# CUE
# ---------------------------------------------------------------------------


def test_valid_cue_calculation(cim_session):
    svc = get_kpi_calculation_service(cim_session)
    result = svc.calculate_cue(
        {"name": "carbon_emission_operational", "value": 250, "unit": "kgCO2e"},
        {"name": "it_equipment_energy", "value": 800, "unit": "kWh"},
        aggregation_period="monthly",
        boundary="facility",
    )
    assert result.calculation_status == "calculated"
    assert result.kpi_namespace == KPI_CUE
    assert result.value == pytest.approx(250 / 800)
    assert result.unit == "kgCO2e/kWh"
    assert result.evidence_requirements
    assert result.provenance_record_id is not None


def test_cue_blocked_by_incompatible_carbon_unit(cim_session):
    svc = get_kpi_calculation_service(cim_session)
    result = svc.calculate_cue(
        {"name": "carbon_emission_operational", "value": 250, "unit": "kWh"},
        {"name": "it_equipment_energy", "value": 800, "unit": "kWh"},
        aggregation_period="monthly",
        boundary="facility",
    )
    assert result.calculation_status == "invalid_unit"
    assert result.value is None


def test_cue_from_carbon_intensity(cim_session):
    svc = get_kpi_calculation_service(cim_session)
    result = svc.calculate_cue(
        {"name": "carbon_intensity", "value": 300, "unit": "gCO2e/kWh"},
        {"name": "it_equipment_energy", "value": 800, "unit": "kWh"},
        aggregation_period="monthly",
        boundary="facility",
        carbon_kind="intensity",
    )
    assert result.calculation_status == "calculated"
    assert result.value == pytest.approx(0.3)


# ---------------------------------------------------------------------------
# Standards / candidate policy
# ---------------------------------------------------------------------------


def test_standards_mapping_attached_only_where_seeded(cim_session):
    svc = get_kpi_calculation_service(cim_session)
    pue = _pue_ok(svc)
    pue_codes = {m.standard_code: m.relation_type for m in pue.standards_mappings}
    assert pue_codes.get("ISO-IEC-30134") == "exactMatch"
    assert pue_codes.get("EN-50600") == "exactMatch"

    wue = svc.calculate_wue(
        {"name": "water_usage_total", "value": 100, "unit": "L"},
        {"name": "it_equipment_energy", "value": 50, "unit": "kWh"},
        aggregation_period="monthly",
        boundary="facility",
    )
    wue_exact = [m for m in wue.standards_mappings if m.relation_type == "exactMatch"]
    assert wue_exact == []


def test_candidate_metric_cannot_produce_approved_reportable_kpi(cim_session):
    metric = (
        cim_session.query(CimMetricDefinition)
        .filter_by(namespace="cim:facility.energy.consumption.total")
        .one()
    )
    metric.status = "candidate"
    metric.review_status = "under_review"
    cim_session.commit()

    svc = get_kpi_calculation_service(cim_session)
    result = _pue_ok(svc)
    assert result.calculation_status == "under_review"
    assert result.reportable_approved is False
    assert result.value == pytest.approx(1.5)  # computed for review, not approved


def test_allow_candidate_inputs_override(cim_session):
    metric = (
        cim_session.query(CimMetricDefinition)
        .filter_by(namespace="cim:facility.energy.consumption.total")
        .one()
    )
    metric.status = "candidate"
    cim_session.commit()

    svc = get_kpi_calculation_service(cim_session)
    result = _pue_ok(svc, allow_candidate_inputs=True)
    assert result.calculation_status == "calculated"
    assert result.reportable_approved is True


def test_mapping_status_candidate_blocks_approved_kpi(cim_session):
    svc = get_kpi_calculation_service(cim_session)
    result = svc.calculate_pue(
        KpiInput(
            name="total_facility_energy",
            value=1200,
            unit="kWh",
            mapping_status="candidate",
        ),
        KpiInput(name="it_equipment_energy", value=800, unit="kWh"),
        aggregation_period="monthly",
        boundary="facility",
    )
    assert result.calculation_status == "under_review"
    assert result.reportable_approved is False


def test_non_reportable_skips_period_boundary(cim_session):
    svc = get_kpi_calculation_service(cim_session)
    result = svc.calculate_pue(
        {"name": "total_facility_energy", "value": 1200, "unit": "kWh"},
        {"name": "it_equipment_energy", "value": 800, "unit": "kWh"},
        reportable=False,
    )
    assert result.calculation_status == "calculated"
    assert result.value == pytest.approx(1.5)


def test_calculate_dispatcher(cim_session):
    svc = get_kpi_calculation_service(cim_session)
    result = svc.calculate(
        "pue",
        total_facility_energy={"value": 1200, "unit": "kWh"},
        it_equipment_energy={"value": 800, "unit": "kWh"},
        aggregation_period="annual",
        boundary="facility",
    )
    assert result.kpi_namespace == KPI_PUE
    assert result.value == pytest.approx(1.5)
