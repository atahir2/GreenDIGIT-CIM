"""Milestone 12: Admin review workflow tests."""

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
from cloud_metrics.registry.extension import ExtensionRegistryService
from cloud_metrics.registry.mapping import MappingRegistryService
from cloud_metrics.registry.mapping.types import MappingEntry
from cloud_metrics.registry.review import (
    AdminReviewService,
    ReviewAction,
    ReviewEntityType,
    get_admin_review_service,
)
from cloud_metrics.registry.seed import seed_all


M2_FILE = (
    Path(__file__).resolve().parents[1]
    / "migrations"
    / "versions"
    / "c2f8a1b9e047_add_cim_registry_tables.py"
)


def _load_m2():
    spec = importlib.util.spec_from_file_location("cim_m2_migration_m12", M2_FILE)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture()
def cim_session(tmp_path):
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


def _make_candidate_mapping(session, source_key: str, namespace: str) -> CimMetricMapping:
    metric = session.query(CimMetricDefinition).filter_by(namespace=namespace).one()
    row = CimMetricMapping(
        source_key=source_key,
        source_id=None,
        metric_id=metric.id,
        relation_type="exactMatch",
        origin="test",
        status="candidate",
        review_status="under_review",
        confidence_score=0.8,
        version=1,
        created_by="m12_test",
    )
    session.add(row)
    session.commit()
    return row


def _prov_actions(session, entity_type: str, entity_id: int):
    return [
        r
        for r in session.query(CimProvenanceRecord)
        .filter_by(entity_type=entity_type, entity_id=entity_id, activity="review_action")
        .all()
    ]


# ---------------------------------------------------------------------------
# Listing
# ---------------------------------------------------------------------------


def test_list_pending_candidates(cim_session):
    _make_candidate_mapping(cim_session, "raw.m12.power", "cim:compute.node.power.draw")
    ext = ExtensionRegistryService(session=cim_session).propose_from_raw(
        "totally_custom_m12_metric"
    )
    cim_session.commit()

    svc = get_admin_review_service(cim_session)
    pending = svc.list_pending(
        entity_types=[ReviewEntityType.MAPPING, ReviewEntityType.EXTENSION]
    )
    keys = {(e.entity_type, e.namespace_or_key) for e in pending}
    assert (ReviewEntityType.MAPPING, "raw.m12.power") in keys
    assert any(e.entity_type == ReviewEntityType.EXTENSION and e.entity_id == ext.id for e in pending)


# ---------------------------------------------------------------------------
# Mapping approve / reject / deprecate / provenance
# ---------------------------------------------------------------------------


def test_approve_candidate_mapping(cim_session):
    row = _make_candidate_mapping(
        cim_session, "raw.m12.approve", "cim:compute.node.power.draw"
    )
    svc = AdminReviewService(session=cim_session)
    decision = svc.approve(
        ReviewEntityType.MAPPING, row.id, reviewer="alice", notes="looks good"
    )
    assert decision.ok
    assert decision.new_status == "approved"
    assert decision.new_review_status == "approved"
    assert decision.provenance_record_id is not None

    refreshed = cim_session.get(CimMetricMapping, row.id)
    assert refreshed.status == "approved"
    assert refreshed.review_status == "approved"
    assert refreshed.approved_by == "alice"
    assert _prov_actions(cim_session, "cim_mapping", row.id)


def test_reject_candidate_mapping(cim_session):
    row = _make_candidate_mapping(
        cim_session, "raw.m12.reject", "cim:compute.node.power.draw"
    )
    svc = get_admin_review_service(cim_session)
    decision = svc.reject(
        ReviewEntityType.MAPPING, row.id, reviewer="bob", notes="wrong metric"
    )
    assert decision.ok
    assert decision.new_status == "rejected"
    refreshed = cim_session.get(CimMetricMapping, row.id)
    assert refreshed.status == "rejected"
    assert refreshed.review_status == "rejected"


def test_rejected_cannot_approve_without_reopen(cim_session):
    row = _make_candidate_mapping(
        cim_session, "raw.m12.noreopen", "cim:compute.node.power.draw"
    )
    svc = get_admin_review_service(cim_session)
    assert svc.reject(ReviewEntityType.MAPPING, row.id, reviewer="bob").ok
    bad = svc.approve(ReviewEntityType.MAPPING, row.id, reviewer="bob")
    assert bad.ok is False
    assert any("rejected" in e.lower() for e in bad.errors)

    reopen = svc.apply(
        ReviewEntityType.MAPPING, row.id, ReviewAction.REOPEN, reviewer="bob"
    )
    assert reopen.ok
    ok = svc.approve(ReviewEntityType.MAPPING, row.id, reviewer="bob")
    assert ok.ok


def test_prevent_duplicate_approved_mapping(cim_session):
    first = _make_candidate_mapping(
        cim_session, "raw.m12.dup", "cim:compute.node.power.draw"
    )
    svc = get_admin_review_service(cim_session)
    assert svc.approve(ReviewEntityType.MAPPING, first.id, reviewer="alice").ok

    # Second candidate same source_key — unique constraint may block insert;
    # simulate by temporarily using a different key then renaming is hard due to unique.
    # Instead create with source_id distinction if possible, or different key then
    # force status conflict via second approved with same key isn't possible under unique.
    # Create another candidate for SAME key by deleting unique conflict path:
    # Use MappingRegistryService.propose which returns existing — so create via different
    # approach: insert with source_id set to a candidate source.
    from cloud_metrics.models.cim_registry import CimSource

    src = CimSource(
        name="dup_source_m12",
        type="test",
        status="candidate",
        review_status="under_review",
        version=1,
    )
    cim_session.add(src)
    cim_session.flush()
    metric = (
        cim_session.query(CimMetricDefinition)
        .filter_by(namespace="cim:compute.node.power.draw")
        .one()
    )
    second = CimMetricMapping(
        source_key="raw.m12.dup",
        source_id=src.id,
        metric_id=metric.id,
        relation_type="exactMatch",
        origin="test",
        status="candidate",
        review_status="under_review",
        version=1,
        created_by="m12_test",
    )
    cim_session.add(second)
    cim_session.commit()

    # Different source_id → not duplicate by unique key; but our validator checks
    # source_key only among approved. First is approved with source_id NULL.
    # Second has same source_key — should be blocked on approve.
    decision = svc.approve(ReviewEntityType.MAPPING, second.id, reviewer="alice")
    assert decision.ok is False
    assert any("duplicate" in e.lower() for e in decision.errors)


def test_deprecate_approved_mapping(cim_session):
    row = _make_candidate_mapping(
        cim_session, "raw.m12.depr", "cim:compute.node.power.draw"
    )
    svc = get_admin_review_service(cim_session)
    assert svc.approve(ReviewEntityType.MAPPING, row.id, reviewer="alice").ok
    decision = svc.apply(
        ReviewEntityType.MAPPING,
        row.id,
        ReviewAction.DEPRECATE,
        reviewer="alice",
        notes="superseded",
    )
    assert decision.ok
    assert decision.new_status == "deprecated"
    assert _prov_actions(cim_session, "cim_mapping", row.id)


# ---------------------------------------------------------------------------
# Merge
# ---------------------------------------------------------------------------


def test_merge_candidate_mapping_into_approved_metric(cim_session):
    # Candidate pointing at CPU util; merge into node power
    row = _make_candidate_mapping(
        cim_session, "raw.m12.merge", "cim:compute.cpu.utilisation"
    )
    svc = get_admin_review_service(cim_session)
    decision = svc.merge(
        ReviewEntityType.MAPPING,
        row.id,
        reviewer="alice",
        merge_target_namespace="cim:compute.node.power.draw",
        notes="better fit",
    )
    assert decision.ok
    refreshed = cim_session.get(CimMetricMapping, row.id)
    target = (
        cim_session.query(CimMetricDefinition)
        .filter_by(namespace="cim:compute.node.power.draw")
        .one()
    )
    assert refreshed.metric_id == target.id
    assert refreshed.status == "approved"
    assert refreshed.review_status == "approved"


# ---------------------------------------------------------------------------
# Extension approval gates
# ---------------------------------------------------------------------------


def test_reject_incomplete_extension_approval(cim_session):
    ext = ExtensionRegistryService(session=cim_session).propose_from_raw(
        "incomplete_ext_m12"
    )
    cim_session.commit()
    svc = get_admin_review_service(cim_session)
    decision = svc.approve(ReviewEntityType.EXTENSION, ext.id, reviewer="alice")
    assert decision.ok is False
    assert decision.errors


def test_approve_extension_when_required_fields_exist(cim_session):
    ext_svc = ExtensionRegistryService(session=cim_session)
    ext = ext_svc.propose_from_raw("complete_ext_m12")
    cim_session.commit()
    svc = get_admin_review_service(cim_session)
    decision = svc.approve(
        ReviewEntityType.EXTENSION,
        ext.id,
        reviewer="alice",
        notes="catalogue ready",
        edits={
            "justification": "Research KPI for GreenDIGIT pilot; reviewed by domain owner",
            "quantity_kind": "Dimensionless",
            "suggested_unit": "score",
            "suggested_definition": "Pilot green score for workflow scheduling",
            "source_context": {"tool": "research_scheduler"},
        },
    )
    assert decision.ok, decision.errors
    row = cim_session.get(CimExtensionMetric, ext.id)
    assert row.status == "approved"
    assert row.review_status == "approved"
    metric = cim_session.get(CimMetricDefinition, row.metric_id)
    assert metric.status == "approved"
    assert metric.review_status == "approved"
    assert metric.quantity_kind_id is not None
    assert _prov_actions(cim_session, "cim_extension", ext.id)


# ---------------------------------------------------------------------------
# Seed promotion
# ---------------------------------------------------------------------------


def test_promote_approved_mapping_to_seed_proposal(cim_session, tmp_path):
    row = _make_candidate_mapping(
        cim_session, "raw.m12.seed", "cim:compute.node.power.draw"
    )
    svc = get_admin_review_service(cim_session)
    assert svc.approve(ReviewEntityType.MAPPING, row.id, reviewer="alice").ok

    # Cannot promote before approval — already approved
    decision = svc.promote_to_seed(
        ReviewEntityType.MAPPING,
        row.id,
        reviewer="alice",
        notes="stable demo mapping",
        seed_output_dir=tmp_path / "seed_out",
    )
    assert decision.ok, decision.errors
    assert decision.seed_proposal_path
    latest = Path(decision.seed_proposal_path)
    assert latest.is_file()
    text = latest.read_text(encoding="utf-8")
    assert "raw.m12.seed" in text
    assert "auto_applied_to_canonical_seed" in text
    # Canonical seed file untouched
    seed_data = (
        Path(__file__).resolve().parents[1]
        / "cloud_metrics"
        / "registry"
        / "seed"
        / "data.py"
    )
    assert "raw.m12.seed" not in seed_data.read_text(encoding="utf-8")


def test_promote_requires_approval(cim_session, tmp_path):
    row = _make_candidate_mapping(
        cim_session, "raw.m12.noseed", "cim:compute.node.power.draw"
    )
    svc = get_admin_review_service(cim_session)
    decision = svc.promote_to_seed(
        ReviewEntityType.MAPPING,
        row.id,
        reviewer="alice",
        seed_output_dir=tmp_path / "seed_out",
    )
    assert decision.ok is False


# ---------------------------------------------------------------------------
# Standards exactMatch guard
# ---------------------------------------------------------------------------


def test_standards_exact_match_requires_explicit_flag(cim_session):
    metric = (
        cim_session.query(CimMetricDefinition)
        .filter_by(namespace="cim:energy.efficiency.pue")
        .one()
    )
    # Find a seeded standards mapping and flip to candidate under_review
    row = (
        cim_session.query(CimMetricMapping)
        .filter(
            CimMetricMapping.metric_id == metric.id,
            CimMetricMapping.standard_id.isnot(None),
        )
        .first()
    )
    assert row is not None
    row.status = "under_review"
    row.review_status = "under_review"
    row.relation_type = "exactMatch"
    cim_session.commit()

    svc = get_admin_review_service(cim_session)
    denied = svc.approve(
        ReviewEntityType.STANDARDS_MAPPING, row.id, reviewer="alice"
    )
    assert denied.ok is False
    assert any("exactmatch" in e.lower() for e in denied.errors)

    allowed = svc.approve(
        ReviewEntityType.STANDARDS_MAPPING,
        row.id,
        reviewer="alice",
        allow_exact_match=True,
    )
    assert allowed.ok, allowed.errors


# ---------------------------------------------------------------------------
# Source candidate approve
# ---------------------------------------------------------------------------


def test_approve_candidate_source(cim_session):
    from cloud_metrics.models.cim_registry import CimSource

    src = CimSource(
        name="prom_m12",
        type="monitoring_system",
        status="candidate",
        review_status="under_review",
        version=1,
        created_by="m12_test",
    )
    cim_session.add(src)
    cim_session.commit()

    svc = get_admin_review_service(cim_session)
    decision = svc.approve(ReviewEntityType.SOURCE, src.id, reviewer="alice")
    assert decision.ok
    refreshed = cim_session.get(CimSource, src.id)
    assert refreshed.status == "approved"
    assert refreshed.review_status == "approved"


def test_provenance_created_for_each_review_action(cim_session):
    row = _make_candidate_mapping(
        cim_session, "raw.m12.prov", "cim:compute.node.power.draw"
    )
    svc = get_admin_review_service(cim_session)
    svc.apply(
        ReviewEntityType.MAPPING,
        row.id,
        ReviewAction.MARK_UNDER_REVIEW,
        reviewer="alice",
    )
    svc.reject(ReviewEntityType.MAPPING, row.id, reviewer="alice", notes="no")
    svc.apply(ReviewEntityType.MAPPING, row.id, ReviewAction.REOPEN, reviewer="alice")
    svc.approve(ReviewEntityType.MAPPING, row.id, reviewer="alice")
    actions = _prov_actions(cim_session, "cim_mapping", row.id)
    assert len(actions) >= 4
    payloads = [a.inputs.get("action") for a in actions]
    assert "mark_under_review" in payloads
    assert "reject" in payloads
    assert "reopen" in payloads
    assert "approve" in payloads
