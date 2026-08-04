"""Milestone 6: Source / Asset registry resolution tests."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from cloud_metrics.models.cim_registry import CimAsset, CimMetricDefinition, CimMetricMapping, CimSource
from cloud_metrics.registry.asset import AssetRegistryService
from cloud_metrics.registry.context_extract import extract_asset_hints, extract_source_hints
from cloud_metrics.registry.mapping import resolve_raw_metric
from cloud_metrics.registry.seed import seed_all
from cloud_metrics.registry.source import SourceRegistryService


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
            created_by="milestone6_test",
        )
    )
    session.commit()


# ---------------------------------------------------------------------------
# Extraction helpers
# ---------------------------------------------------------------------------


def test_extract_prometheus_like_source():
    hints = extract_source_hints(
        {"job": "node_exporter", "instance": "hpc-node-07:9100", "labels": {"__name__": "node_cpu"}}
    )
    assert hints.name == "node_exporter"
    assert hints.type == "monitoring_system"
    assert hints.confidence > 0


def test_extract_file_and_api_source():
    file_hints = extract_source_hints({"file_name": "batch_metrics.json"})
    assert file_hints.type == "file"
    assert file_hints.name == "batch_metrics.json"

    api_hints = extract_source_hints({"api_name": "partner_metrics_api", "source_type": "api"})
    assert api_hints.type == "api"
    assert api_hints.name == "partner_metrics_api"


def test_extract_asset_hierarchy_hints():
    hints = extract_asset_hints(
        {
            "site": "RI-site-1",
            "cluster": "cluster-A",
            "node": "hpc-node-07",
            "gpu_id": "gpu-0",
        }
    )
    assert hints.site == "RI-site-1"
    assert hints.cluster == "cluster-A"
    assert hints.node == "hpc-node-07"
    assert hints.gpu == "gpu-0"
    assert hints.primary_type == "gpu"
    assert hints.primary_identifier == "gpu-0"


# ---------------------------------------------------------------------------
# Source registry
# ---------------------------------------------------------------------------


def test_prometheus_like_source_resolution(cim_session):
    svc = SourceRegistryService(session=cim_session)
    result = svc.resolve_from_metadata(
        {"job": "node_exporter", "instance": "host:9100"}
    )
    assert result.resolution_status == "candidate_created"
    assert result.source_name == "node_exporter"
    assert result.source_type == "monitoring_system"
    assert result.source_id is not None


def test_file_upload_and_api_source_resolution(cim_session):
    svc = SourceRegistryService(session=cim_session)
    file_res = svc.resolve_from_metadata({"file_name": "upload.csv", "source_type": "file"})
    assert file_res.resolution_status == "candidate_created"
    assert file_res.source_type == "file"

    api_res = svc.resolve_from_metadata({"api_name": "metrics_api", "source_type": "rest"})
    assert api_res.resolution_status == "candidate_created"
    assert api_res.source_type == "api"


def test_unknown_source_candidate_or_missing(cim_session):
    svc = SourceRegistryService(session=cim_session)
    created = svc.resolve_or_create(
        name="brand_new_collector",
        source_type="monitoring_system",
        create_candidate=True,
    )
    assert created.resolution_status == "candidate_created"

    missing = svc.resolve_or_create(
        name="never_seen_source",
        source_type="api",
        create_candidate=False,
    )
    assert missing.resolution_status == "missing"


def test_duplicate_source_prevention(cim_session):
    svc = SourceRegistryService(session=cim_session)
    first = svc.resolve_or_create(name="dup_src", source_type="file", create_candidate=True)
    second = svc.resolve_or_create(name="dup_src", source_type="file", create_candidate=True)
    assert first.source_id == second.source_id
    assert second.resolution_status == "resolved"
    assert cim_session.query(CimSource).filter_by(name="dup_src").count() == 1


def test_source_skeleton_without_session():
    svc = SourceRegistryService()
    assert svc.list_entries() == []
    assert svc.get_by_name("x") is None


# ---------------------------------------------------------------------------
# Asset registry
# ---------------------------------------------------------------------------


def test_node_asset_creation(cim_session):
    svc = AssetRegistryService(session=cim_session)
    result = svc.resolve_or_create(
        identifier="hpc-node-07", asset_type="node", create_candidate=True
    )
    assert result.resolution_status == "candidate_created"
    assert result.asset_type == "node"
    assert result.asset_id is not None


def test_cluster_node_hierarchy(cim_session):
    svc = AssetRegistryService(session=cim_session)
    result = svc.resolve_from_metadata(
        {"cluster": "cluster-A", "node": "hpc-node-07"}
    )
    assert result.asset_identifier == "hpc-node-07"
    assert result.asset_type == "node"
    assert result.parent_asset_id is not None
    parent = cim_session.get(CimAsset, result.parent_asset_id)
    assert parent is not None
    assert parent.identifier == "cluster-A"
    assert parent.type == "cluster"


def test_gpu_under_node_hierarchy(cim_session):
    svc = AssetRegistryService(session=cim_session)
    result = svc.resolve_from_metadata(
        {
            "site": "RI-site-1",
            "cluster": "cluster-A",
            "node": "hpc-node-07",
            "gpu_id": "gpu-0",
        }
    )
    assert result.asset_identifier == "gpu-0"
    assert result.asset_type == "gpu"
    assert result.parent_asset_id is not None
    node = cim_session.get(CimAsset, result.parent_asset_id)
    assert node.identifier == "hpc-node-07"
    assert node.type == "node"
    # site → cluster → node → gpu
    assert len(result.hierarchy) >= 3


def test_workflow_and_workflow_run(cim_session):
    svc = AssetRegistryService(session=cim_session)
    result = svc.resolve_from_metadata(
        {"workflow_id": "wf-204", "workflow_run_id": "run-001"}
    )
    assert result.asset_identifier == "run-001"
    assert result.asset_type == "workflow_run"
    parent = cim_session.get(CimAsset, result.parent_asset_id)
    assert parent.identifier == "wf-204"
    assert parent.type == "workflow"


def test_dataset_and_experiment_assets(cim_session):
    svc = AssetRegistryService(session=cim_session)
    ds = svc.resolve_or_create(
        identifier="ds-42", asset_type="dataset", create_candidate=True
    )
    exp = svc.resolve_or_create(
        identifier="exp-7", asset_type="experiment", create_candidate=True
    )
    assert ds.resolution_status == "candidate_created"
    assert exp.resolution_status == "candidate_created"


def test_duplicate_asset_prevention(cim_session):
    svc = AssetRegistryService(session=cim_session)
    a = svc.resolve_or_create(identifier="node-1", asset_type="node")
    b = svc.resolve_or_create(identifier="node-1", asset_type="node")
    assert a.asset_id == b.asset_id
    assert b.resolution_status == "resolved"
    assert (
        cim_session.query(CimAsset)
        .filter(
            func.lower(CimAsset.identifier) == "node-1",
            CimAsset.type == "node",
        )
        .count()
        == 1
    )


def test_asset_skeleton_without_session():
    svc = AssetRegistryService()
    assert svc.list_entries() == []
    assert svc.get_by_id(1) is None


# ---------------------------------------------------------------------------
# Mapping lookup integration
# ---------------------------------------------------------------------------


def test_mapping_result_includes_source_and_asset(cim_session):
    _ensure_raw_mapping(
        cim_session, "raw.node.power.m6", "cim:compute.node.power.draw"
    )
    result = resolve_raw_metric(
        "raw.node.power.m6",
        session=cim_session,
        use_fallback=False,
        observed_unit="W",
        context={
            "source": "prometheus",
            "source_type": "prometheus",
            "job": "node_exporter",
            "cluster": "cluster-A",
            "node": "hpc-node-07",
        },
    )
    assert result.resolved is True
    assert result.unit_validation is not None
    assert result.source_resolution is not None
    assert result.source_resolution.resolution_status in {
        "resolved",
        "candidate_created",
    }
    assert result.asset_resolution is not None
    assert result.asset_resolution.asset_identifier == "hpc-node-07"
    assert result.asset_resolution.asset_type == "node"


def test_mapping_without_context_still_works(cim_session):
    _ensure_raw_mapping(
        cim_session, "raw.energy.m6", "cim:energy.consumption.total"
    )
    result = resolve_raw_metric(
        "raw.energy.m6", session=cim_session, use_fallback=False
    )
    assert result.resolved is True
    assert result.source_resolution is None
    assert result.asset_resolution is None


def test_missing_source_asset_does_not_fail_mapping(cim_session):
    _ensure_raw_mapping(
        cim_session, "raw.energy.m6b", "cim:energy.consumption.total"
    )
    result = resolve_raw_metric(
        "raw.energy.m6b",
        session=cim_session,
        use_fallback=False,
        context={},  # empty → missing statuses
        resolve_source=True,
        resolve_asset=True,
        create_source_candidate=False,
        create_asset_candidate=False,
    )
    assert result.resolved is True
    assert result.source_resolution is not None
    assert result.source_resolution.resolution_status == "missing"
    assert result.asset_resolution is not None
    assert result.asset_resolution.resolution_status == "missing"
