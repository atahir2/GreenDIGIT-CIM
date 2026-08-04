"""Synchronize discovered legacy mappings into ``cim_metric_*`` tables."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set

from sqlalchemy import func
from sqlalchemy.orm import Session

from cloud_metrics.models.cim_registry import CimMetricDefinition, CimMetricMapping
from cloud_metrics.registry.migration.gd_to_cim import resolve_cim_namespace
from cloud_metrics.registry.migration.legacy_sources import (
    DiscoveryReport,
    LegacyMappingRecord,
    discover_legacy_mappings,
)

logger = logging.getLogger(__name__)

CREATED_BY = "milestone4_migration"
ACTIVE_STATUSES = frozenset({"approved", "active"})


@dataclass
class MigrationReport:
    discovered: int = 0
    mappings_created: int = 0
    mappings_skipped_duplicate: int = 0
    candidate_metrics_created: int = 0
    metrics_linked_existing: int = 0
    skipped_uncategorized: int = 0
    skipped_noise: int = 0
    by_source: Dict[str, int] = field(default_factory=dict)
    linked_namespaces: Set[str] = field(default_factory=set)
    candidate_namespaces: Set[str] = field(default_factory=set)
    errors: List[str] = field(default_factory=list)

    def as_dict(self) -> Dict[str, object]:
        return {
            "discovered": self.discovered,
            "mappings_created": self.mappings_created,
            "mappings_skipped_duplicate": self.mappings_skipped_duplicate,
            "candidate_metrics_created": self.candidate_metrics_created,
            "metrics_linked_existing": self.metrics_linked_existing,
            "skipped_uncategorized": self.skipped_uncategorized,
            "skipped_noise": self.skipped_noise,
            "by_source": dict(self.by_source),
            "linked_namespaces": sorted(self.linked_namespaces),
            "candidate_namespaces": sorted(self.candidate_namespaces),
            "errors": list(self.errors),
        }


def _find_mapping(
    session: Session, source_key: str, source_id: Optional[int] = None
) -> Optional[CimMetricMapping]:
    q = session.query(CimMetricMapping).filter(
        func.lower(CimMetricMapping.source_key) == source_key.lower()
    )
    if source_id is None:
        q = q.filter(CimMetricMapping.source_id.is_(None))
    else:
        q = q.filter(CimMetricMapping.source_id == source_id)
    return q.first()


def _get_or_create_metric(
    session: Session,
    cim_namespace: str,
    record: LegacyMappingRecord,
    trusted: bool,
    report: MigrationReport,
) -> CimMetricDefinition:
    existing = (
        session.query(CimMetricDefinition)
        .filter_by(namespace=cim_namespace)
        .first()
    )
    if existing:
        if existing.status in ACTIVE_STATUSES:
            report.metrics_linked_existing += 1
            report.linked_namespaces.add(cim_namespace)
        else:
            report.candidate_namespaces.add(cim_namespace)
        return existing

    # Only create candidates for missing namespaces — never auto-approve.
    label = (
        record.short_key
        or cim_namespace.rsplit(".", 1)[-1]
        or cim_namespace
    )
    metric = CimMetricDefinition(
        namespace=cim_namespace,
        label=str(label).replace("_", " ").title(),
        description=record.description
        or f"Candidate metric migrated from legacy key {record.legacy_unified_key}",
        domain=record.category,
        category=record.category,
        subcategory=record.subcategory,
        metric_type="observed",
        status="candidate",
        review_status="under_review",
        confidence_score=record.confidence,
        version=1,
        created_by=CREATED_BY,
        notes=(
            f"Created during Milestone 4 migration. "
            f"Legacy unified key: {record.legacy_unified_key}. "
            f"Trusted alignment={trusted}. "
            f"{record.notes or ''}"
        ).strip(),
        tags=["migrated", "candidate", record.source_name],
        sources=[record.source_system] if record.source_system else [],
    )
    session.add(metric)
    session.flush()
    report.candidate_metrics_created += 1
    report.candidate_namespaces.add(cim_namespace)
    logger.info(
        "candidate metric definition created: namespace=%s legacy=%s",
        cim_namespace,
        record.legacy_unified_key,
    )
    return metric


def _mapping_status_for_metric(metric: CimMetricDefinition) -> tuple[str, str]:
    if metric.status in ACTIVE_STATUSES and metric.review_status == "approved":
        return "approved", "approved"
    return "candidate", "under_review"


def _upsert_mapping(
    session: Session,
    record: LegacyMappingRecord,
    metric: CimMetricDefinition,
    cim_namespace: str,
    report: MigrationReport,
) -> None:
    existing = _find_mapping(session, record.raw_key, source_id=None)
    if existing:
        report.mappings_skipped_duplicate += 1
        logger.info(
            "duplicate mapping skipped: raw=%s existing_id=%s metric_id=%s",
            record.raw_key,
            existing.id,
            existing.metric_id,
        )
        return

    map_status, review_status = _mapping_status_for_metric(metric)
    now = datetime.now(timezone.utc)
    mapping = CimMetricMapping(
        source_key=record.raw_key,
        source_id=None,
        metric_id=metric.id,
        relation_type="exactMatch" if map_status == "approved" else "underReview",
        rationale=(
            f"Migrated from {record.source_name}. "
            f"Legacy unified={record.legacy_unified_key} → {cim_namespace}."
        ),
        origin="migrated",
        approved_by=CREATED_BY if map_status == "approved" else None,
        approved_at=now if map_status == "approved" else None,
        status=map_status,
        review_status=review_status,
        confidence_score=record.confidence,
        version=1,
        created_by=CREATED_BY,
        notes=record.notes,
    )
    session.add(mapping)
    report.mappings_created += 1
    logger.info(
        "registry mapping created: raw=%s → %s status=%s origin=%s",
        record.raw_key,
        cim_namespace,
        map_status,
        record.source_name,
    )


def migrate_legacy_mappings(
    session: Session,
    *,
    discovery: Optional[DiscoveryReport] = None,
    commit: bool = True,
    skip_uncategorized: bool = True,
) -> MigrationReport:
    """Idempotently write legacy mappings into Metric + Mapping registries."""
    disc = discovery or discover_legacy_mappings()
    report = MigrationReport(
        discovered=len(disc.records),
        skipped_noise=disc.skipped_noise,
        skipped_uncategorized=disc.skipped_uncategorized,
        by_source=dict(disc.by_source),
    )

    for record in disc.records:
        try:
            if skip_uncategorized and record.legacy_unified_key.startswith(
                "gd.uncategorized."
            ):
                report.skipped_uncategorized += 1
                continue

            cim_ns, trusted = resolve_cim_namespace(record.legacy_unified_key)
            metric = _get_or_create_metric(
                session, cim_ns, record, trusted, report
            )
            _upsert_mapping(session, record, metric, cim_ns, report)
        except Exception as exc:  # pragma: no cover - defensive
            msg = f"{record.raw_key}: {exc}"
            report.errors.append(msg)
            logger.exception("mapping migration failed for %s", record.raw_key)

    if commit:
        session.commit()
    else:
        session.flush()

    logger.info(
        "legacy mapping migration complete: discovered=%s created=%s "
        "duplicates=%s candidates=%s linked=%s",
        report.discovered,
        report.mappings_created,
        report.mappings_skipped_duplicate,
        report.candidate_metrics_created,
        report.metrics_linked_existing,
    )
    return report
