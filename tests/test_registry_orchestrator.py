"""Milestone 7: Registry Orchestrator + unified ingestion wiring tests."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from cloud_metrics.models.cim_registry import CimMetricDefinition, CimMetricMapping
from cloud_metrics.registry.orchestrator import (
    OrchestratorResult,
    RawMetricContext,
    RegistryOrchestratorService,
    cim_namespace_to_storage_key,
    get_registry_orchestrator,
)
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
            created_by="milestone7_test",
        )
    )
    session.commit()


# ---------------------------------------------------------------------------
# Storage key adapter
# ---------------------------------------------------------------------------


def test_cim_namespace_to_storage_key():
    assert cim_namespace_to_storage_key("cim:energy.power.total") == "gd.energy.power.total"
    assert cim_namespace_to_storage_key("gd.energy.power.total") == "gd.energy.power.total"
    assert cim_namespace_to_storage_key(None) is None


# ---------------------------------------------------------------------------
# Full registry-driven path
# ---------------------------------------------------------------------------


def test_known_metric_full_registry_driven_path(cim_session):
    _ensure_raw_mapping(cim_session, "orch_power_total", "cim:energy.power.total")
    orch = get_registry_orchestrator(cim_session)
    result = orch.process(
        RawMetricContext(
            raw_metric_name="orch_power_total",
            value=1200.0,
            unit="W",
        )
    )
    assert result.resolved is True
    assert result.fallback_used is False
    assert result.resolution_path == "registry"
    assert result.cim_namespace == "cim:energy.power.total"
    assert result.mapping_status in {"approved", "active"}
    assert result.storage_unified_key == "gd.energy.power.total"
    assert result.metric_definition_id is not None
    assert result.candidate_flags.get("metric_unresolved") is False


def test_known_metric_with_valid_unit(cim_session):
    _ensure_raw_mapping(cim_session, "orch_energy_kwh", "cim:energy.consumption.total")
    orch = RegistryOrchestratorService(session=cim_session)
    result = orch.process(
        RawMetricContext(raw_metric_name="orch_energy_kwh", value=2.5, unit="kWh")
    )
    assert result.resolved is True
    assert result.unit_validation_status == "valid"
    assert result.canonical_unit == "kWh"
    assert result.expected_quantity_kind == "Energy"
    assert result.candidate_flags.get("unit_incompatible") is False


def test_known_metric_with_incompatible_unit(cim_session):
    _ensure_raw_mapping(cim_session, "orch_energy_bad_unit", "cim:energy.consumption.total")
    orch = get_registry_orchestrator(cim_session)
    result = orch.process(
        RawMetricContext(raw_metric_name="orch_energy_bad_unit", value=100.0, unit="W")
    )
    assert result.resolved is True  # soft validation — does not block
    assert result.unit_validation_status == "incompatible"
    assert result.candidate_flags.get("unit_incompatible") is True
    assert any("incompatible" in w.lower() or "unit" in w.lower() for w in result.warnings)


def test_known_metric_with_source_and_asset_metadata(cim_session):
    _ensure_raw_mapping(cim_session, "orch_cpu_util", "cim:compute.cpu.utilisation")
    orch = get_registry_orchestrator(cim_session)
    result = orch.process(
        RawMetricContext(
            raw_metric_name="orch_cpu_util",
            value=0.42,
            unit="%",
            source="node_exporter",
            source_type="monitoring_system",
            source_metadata={"job": "node_exporter", "instance": "node-01:9100"},
            asset_labels={
                "node": "hpc-node-01",
                "host": "hpc-node-01",
                "cluster": "cluster-A",
            },
        )
    )
    assert result.resolved is True
    assert result.source_resolution_status in {"resolved", "candidate_created"}
    assert result.source_id is not None
    assert result.asset_resolution_status in {"resolved", "candidate_created"}
    assert result.asset_id is not None


def test_known_metric_without_source_asset_metadata_still_works(cim_session):
    _ensure_raw_mapping(cim_session, "orch_mem_usage", "cim:compute.memory.usage")
    orch = get_registry_orchestrator(cim_session)
    result = orch.process(
        RawMetricContext(raw_metric_name="orch_mem_usage", value=8.0, unit="GB")
    )
    assert result.resolved is True
    assert result.cim_namespace == "cim:compute.memory.usage"
    # No context → source/asset not requested
    assert result.source_resolution_status is None
    assert result.asset_resolution_status is None
    assert result.source_id is None
    assert result.asset_id is None


def test_unknown_metric_returns_candidate_or_unresolved(cim_session):
    orch = get_registry_orchestrator(cim_session)
    result = orch.process(
        RawMetricContext(
            raw_metric_name="totally_unknown_metric_xyz_m7",
            value=1.0,
        ),
        use_fallback=True,
        create_candidate_on_fallback=False,
    )
    # May resolve via legacy fallback OR stay unresolved — never silently approved
    if result.resolved:
        assert result.fallback_used is True or result.mapping_status == "candidate"
        assert result.mapping_status != "approved" or result.fallback_used
    else:
        assert result.mapping_status == "unresolved"
        assert result.candidate_flags.get("metric_unresolved") is True
        assert result.mapping_status != "approved"


def test_legacy_fallback_still_works(cim_session):
    """energy_wh is in metric_mapping.json / aliases — fallback without registry row."""
    # Ensure no approved registry mapping for a unique key that legacy knows.
    # Use energy_wh which legacy maps; if migration already seeded it, delete approved
    # rows for a synthetic key that only legacy can resolve.
    orch = get_registry_orchestrator(cim_session)

    # Prefer a raw key present in JSON/aliases but not yet in cim_metric_mappings
    existing = (
        cim_session.query(CimMetricMapping)
        .filter_by(source_key="energy_wh")
        .first()
    )
    if existing is not None:
        cim_session.delete(existing)
        cim_session.commit()

    result = orch.process(
        RawMetricContext(raw_metric_name="energy_wh", value=100.0, unit="Wh"),
        use_fallback=True,
        create_candidate_on_fallback=True,
    )
    assert result.resolved is True
    assert result.fallback_used is True
    assert result.resolution_path == "legacy_fallback"
    assert result.cim_namespace == "cim:energy.consumption.total"
    assert result.mapping_status == "candidate"
    assert result.storage_unified_key == "gd.energy.consumption.total"


# ---------------------------------------------------------------------------
# Unified ingestion path uses orchestrator
# ---------------------------------------------------------------------------


def test_unified_ingestion_uses_orchestrator(tmp_path):
    sample = tmp_path / "sample_m7.json"
    sample.write_text('{"PowerTotal_W": 500.0}', encoding="utf-8")

    calls = {"n": 0}

    def _fake_parse(file_path, datacenter):
        return {"PowerTotal_W": 500.0}, {}

    def _fake_process(**kwargs):
        calls["n"] += 1
        assert kwargs.get("use_registry_orchestrator") is True
        return "gd.energy.power.total"

    with patch(
        "cloud_metrics.ingestion.unified_ingestion.parse_and_extract_file_metrics",
        side_effect=_fake_parse,
    ), patch(
        "cloud_metrics.ingestion.unified_ingestion.process_metric_sample",
        side_effect=_fake_process,
    ), patch(
        "cloud_metrics.ingestion.unified_ingestion.insert_datacenter"
    ), patch(
        "cloud_metrics.ingestion.unified_ingestion.write_external_metrics_json"
    ), patch(
        "cloud_metrics.ingestion.unified_ingestion.write_mapped_metrics"
    ), patch(
        "cloud_metrics.ingestion.unified_ingestion.get_or_create_datacenter_id",
        return_value=1,
    ), patch(
        "cloud_metrics.ingestion.unified_ingestion.insert_file_upload_log"
    ), patch(
        "cloud_metrics.ingestion.unified_ingestion.insert_metric_definition"
    ), patch(
        "cloud_metrics.ingestion.unified_ingestion.build_metadata",
        return_value={},
    ):
        from cloud_metrics.ingestion.unified_ingestion import ingest_from_file

        ingest_from_file(str(sample), "test-dc")

    assert calls["n"] == 1


def test_unified_ingestion_can_opt_out_of_orchestrator(tmp_path):
    sample = tmp_path / "sample_m7b.json"
    sample.write_text('{"x": 1.0}', encoding="utf-8")
    seen = {}

    def _fake_process(**kwargs):
        seen["flag"] = kwargs.get("use_registry_orchestrator")
        return "gd.uncategorized.unknown.unknown"

    with patch(
        "cloud_metrics.ingestion.unified_ingestion.parse_and_extract_file_metrics",
        return_value=({"x": 1.0}, {}),
    ), patch(
        "cloud_metrics.ingestion.unified_ingestion.process_metric_sample",
        side_effect=_fake_process,
    ), patch(
        "cloud_metrics.ingestion.unified_ingestion.insert_datacenter"
    ), patch(
        "cloud_metrics.ingestion.unified_ingestion.write_external_metrics_json"
    ), patch(
        "cloud_metrics.ingestion.unified_ingestion.write_mapped_metrics"
    ), patch(
        "cloud_metrics.ingestion.unified_ingestion.get_or_create_datacenter_id",
        return_value=1,
    ), patch(
        "cloud_metrics.ingestion.unified_ingestion.insert_file_upload_log"
    ), patch(
        "cloud_metrics.ingestion.unified_ingestion.insert_metric_definition"
    ), patch(
        "cloud_metrics.ingestion.unified_ingestion.build_metadata",
        return_value={},
    ):
        from cloud_metrics.ingestion.unified_ingestion import ingest_from_file

        ingest_from_file(str(sample), "test-dc", use_registry_orchestrator=False)

    assert seen["flag"] is False


def test_process_metric_sample_default_skips_orchestrator():
    """Existing callers without the flag must not invoke the orchestrator."""
    with patch(
        "cloud_metrics.ingestion.automated_mapper._run_registry_orchestrator"
    ) as orch_run, patch(
        "cloud_metrics.ingestion.automated_mapper.get_or_create_datacenter_id",
        return_value=1,
    ), patch(
        "cloud_metrics.ingestion.automated_mapper.SessionLocal"
    ) as sess_local, patch(
        "cloud_metrics.ingestion.automated_mapper.classify_metric"
    ) as classify, patch(
        "cloud_metrics.ingestion.automated_mapper.ensure_gd_namespace",
        return_value="gd.energy.power.total",
    ), patch(
        "cloud_metrics.ingestion.automated_mapper.resolve_mapping",
        create=True,
    ), patch(
        "cloud_metrics.services.mapping_registry_service.resolve_mapping",
        return_value=None,
    ), patch(
        "cloud_metrics.services.rule_registry_service.validate_metric_sample",
        return_value=[],
    ), patch(
        "cloud_metrics.ingestion.automated_mapper.register_mapping"
    ), patch(
        "cloud_metrics.ingestion.automated_mapper.insert_mapped_metric"
    ), patch(
        "cloud_metrics.ingestion.automated_mapper.insert_metric_sample",
        return_value=1,
    ), patch(
        "cloud_metrics.ingestion.automated_mapper.sync_metric_mapping"
    ):
        # SessionLocal context manager for legacy Asset/Source + unit blocks
        fake_session = MagicMock()
        fake_session.query.return_value.filter_by.return_value.first.return_value = None
        fake_session.__enter__ = MagicMock(return_value=fake_session)
        fake_session.__exit__ = MagicMock(return_value=False)
        sess_local.return_value = fake_session

        decision = MagicMock()
        decision.category = "energy"
        decision.subcategory = "power"
        decision.short_key = "total"
        decision.confidence = 0.9
        decision.rationale = "test"
        classify.return_value = decision

        from cloud_metrics.ingestion.automated_mapper import process_metric_sample

        key = process_metric_sample(
            raw_key="PowerDraw",
            value=10.0,
            origin="dc-a",
            # default use_registry_orchestrator=False
        )
        assert key == "gd.energy.power.total"
        orch_run.assert_not_called()


def test_orchestrator_result_to_metadata_roundtrip():
    r = OrchestratorResult(
        raw_metric_name="x",
        cim_namespace="cim:energy.power.total",
        mapping_status="approved",
        fallback_used=False,
        resolved=True,
        warnings=["note"],
    )
    meta = r.to_metadata()
    assert meta["cim_namespace"] == "cim:energy.power.total"
    assert meta["warnings"] == ["note"]
    assert meta["fallback_used"] is False
