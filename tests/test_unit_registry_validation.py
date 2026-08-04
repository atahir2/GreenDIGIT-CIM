"""Milestone 5: Unit Registry + quantity-kind validation tests."""

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
from cloud_metrics.registry.mapping import resolve_raw_metric
from cloud_metrics.registry.unit import UnitRegistryService, resolve_unit_alias
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


@pytest.fixture()
def units(cim_session):
    return UnitRegistryService(session=cim_session)


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
            created_by="milestone5_test",
        )
    )
    session.commit()


# ---------------------------------------------------------------------------
# Alias / lookup
# ---------------------------------------------------------------------------


def test_unit_aliases_resolve():
    assert resolve_unit_alias("watts") == "W"
    assert resolve_unit_alias("kwh") == "kWh"
    assert resolve_unit_alias("gb") == "GB"
    assert resolve_unit_alias("percent") == "%"


def test_get_by_symbol_and_quantity_kind(units):
    w = units.get_by_symbol("W")
    assert w is not None
    assert w.quantity_kind == "Power"
    assert w.canonical_unit_symbol == "W"

    kw = units.get_by_alias("kilowatt")
    assert kw is not None
    assert kw.symbol == "kW"
    assert kw.quantity_kind == "Power"

    canon = units.get_canonical_unit("Energy")
    assert canon is not None
    assert canon.symbol == "kWh"


def test_skeleton_without_session_still_empty():
    svc = UnitRegistryService()
    assert svc.list_entries() == []
    assert svc.get_by_symbol("W") is None


# ---------------------------------------------------------------------------
# Direct metric / quantity-kind validation cases
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "namespace,observed,expected_status",
    [
        ("cim:compute.node.power.draw", "W", "valid"),
        ("cim:compute.node.power.draw", "kW", "normalized"),
        ("cim:compute.node.power.draw", "kWh", "incompatible"),
        ("cim:energy.consumption.total", "kWh", "valid"),
        ("cim:energy.consumption.total", "W", "incompatible"),
        ("cim:carbon.emission.operational", "kgCO2e", "valid"),
        ("cim:carbon.intensity.location_based", "gCO2e/kWh", "valid"),
        ("cim:workflow.execution.duration", "s", "valid"),
        ("cim:compute.memory.usage", "GB", "normalized"),  # canonical B
        ("cim:water.usage.total", "L", "valid"),
        ("cim:water.usage.total", "m3", "normalized"),
    ],
)
def test_validate_for_seeded_metrics(units, namespace, observed, expected_status):
    result = units.validate_for_metric(namespace, observed)
    assert result.validation_status == expected_status
    if expected_status == "incompatible":
        assert result.severity == "error"
        assert not result.ok
    else:
        assert result.ok


def test_dimensionless_allows_missing_and_score(units):
    missing = units.validate_observed_unit(
        observed_unit=None,
        expected_quantity_kind="Dimensionless",
        canonical_unit="dimensionless",
    )
    assert missing.validation_status == "valid"
    assert missing.ok

    score = units.validate_observed_unit(
        observed_unit="score",
        expected_quantity_kind="Dimensionless",
        canonical_unit="dimensionless",
    )
    assert score.validation_status in {"valid", "normalized"}
    assert score.ok

    # Power with score is incompatible
    bad = units.validate_observed_unit(
        observed_unit="score",
        expected_quantity_kind="Power",
        canonical_unit="W",
    )
    assert bad.validation_status == "incompatible"


def test_missing_unit_for_numeric_metric_warns(units):
    result = units.validate_for_metric("cim:compute.node.power.draw", None)
    assert result.validation_status == "missing"
    assert result.severity == "warning"


def test_unknown_unit_warns(units):
    result = units.validate_for_metric(
        "cim:compute.node.power.draw", "furlongs_per_fortnight"
    )
    assert result.validation_status == "unknown"
    assert result.severity == "warning"


def test_quantity_kind_distinguishes_power_energy_carbon(units):
    assert units.units_compatible("W", "Power")
    assert units.units_compatible("kWh", "Energy")
    assert not units.units_compatible("kWh", "Power")
    assert units.units_compatible("kgCO2e", "CarbonEmission")
    assert units.units_compatible("gCO2e/kWh", "CarbonIntensity")
    assert units.units_compatible("s", "Time")
    assert units.units_compatible("GB", "DataSize")
    assert units.units_compatible("%", "Ratio")
    assert units.units_compatible("dimensionless", "Dimensionless")
    assert units.units_compatible("L", "WaterVolume")
    assert units.units_compatible("count", "Count")


# ---------------------------------------------------------------------------
# Integration with registry-first mapping lookup
# ---------------------------------------------------------------------------


def test_mapping_lookup_attaches_unit_validation(cim_session, units):
    _ensure_raw_mapping(
        cim_session, "raw.node.power", "cim:compute.node.power.draw"
    )
    ok = resolve_raw_metric(
        "raw.node.power",
        session=cim_session,
        observed_unit="W",
        use_fallback=False,
    )
    assert ok.resolved is True
    assert ok.unit_validation is not None
    assert ok.unit_validation.validation_status == "valid"
    assert ok.expected_quantity_kind == "Power"
    assert ok.canonical_unit == "W"

    bad = resolve_raw_metric(
        "raw.node.power",
        session=cim_session,
        observed_unit="kWh",
        use_fallback=False,
    )
    assert bad.resolved is True  # soft — does not break caller
    assert bad.unit_validation.validation_status == "incompatible"
    assert bad.unit_validation.severity == "error"


def test_mapping_lookup_without_unit_skips_validation_by_default(cim_session):
    _ensure_raw_mapping(
        cim_session, "raw.energy.total", "cim:energy.consumption.total"
    )
    result = resolve_raw_metric(
        "raw.energy.total", session=cim_session, use_fallback=False
    )
    assert result.resolved is True
    assert result.unit_validation is None


def test_mapping_lookup_explicit_missing_unit_check(cim_session):
    _ensure_raw_mapping(
        cim_session, "raw.energy.total2", "cim:energy.consumption.total"
    )
    result = resolve_raw_metric(
        "raw.energy.total2",
        session=cim_session,
        use_fallback=False,
        validate_unit=True,
        observed_unit=None,
    )
    assert result.resolved is True
    assert result.unit_validation is not None
    assert result.unit_validation.validation_status == "missing"


def test_legacy_fallback_still_works_with_unit_check(cim_session):
    # alpha.cpu is in metric_mapping.json → gd.performance.cpu.utilization
    result = resolve_raw_metric(
        "alpha.cpu",
        session=cim_session,
        use_fallback=True,
        observed_unit="%",
    )
    assert result.resolved is True
    assert result.resolution_path == "legacy_fallback"
    assert result.cim_namespace == "cim:compute.cpu.utilisation"
    assert result.unit_validation is not None
    # utilisation is Ratio with canonical %
    assert result.unit_validation.validation_status in {"valid", "normalized"}


def test_unknown_metric_preserves_unresolved(cim_session):
    result = resolve_raw_metric(
        "totally_unknown_metric_xyz_999",
        session=cim_session,
        observed_unit="W",
    )
    assert result.resolved is False
    assert result.status == "unresolved"
    assert result.unit_validation is None
