"""Standards Registry service — Milestone 8.

Retrieves seeded standard catalogue entries and metric↔standard mappings.
Does not invent exactMatch claims.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from sqlalchemy.orm import Session

from cloud_metrics.registry.base import RegistryName, SKELETON_ONLY
from cloud_metrics.registry.standards.types import (
    StandardEntry,
    StandardMappingEntry,
    StandardsLookupResult,
)

logger = logging.getLogger(__name__)

_ACTIVE_MAPPING = frozenset({"approved", "active"})
_ACTIVE_METRIC = frozenset({"approved", "active"})


class StandardsRegistryService:
    """Standards Registry with optional DB session."""

    registry_name = RegistryName.STANDARDS
    skeleton_only = SKELETON_ONLY

    def __init__(self, session: Optional[Session] = None) -> None:
        self._session = session

    def list_entries(self) -> List[StandardEntry]:
        if self._session is None:
            return []
        from cloud_metrics.models.cim_registry import CimStandard

        rows = self._session.query(CimStandard).order_by(CimStandard.code.asc()).all()
        return [self._to_entry(r) for r in rows]

    def get_by_code(self, code: str) -> Optional[StandardEntry]:
        if self._session is None or not code:
            return None
        from cloud_metrics.models.cim_registry import CimStandard

        row = (
            self._session.query(CimStandard)
            .filter(CimStandard.code == code.strip())
            .first()
        )
        return self._to_entry(row) if row else None

    def register(self, entry: StandardEntry) -> StandardEntry:
        """Echo / optional persist — does not auto-approve."""
        if self._session is None:
            return entry
        from cloud_metrics.models.cim_registry import CimStandard

        existing = (
            self._session.query(CimStandard).filter_by(code=entry.code).first()
        )
        if existing:
            return self._to_entry(existing)
        row = CimStandard(
            code=entry.code,
            name=entry.name,
            standard_version=entry.version,
            url=entry.url,
            description=entry.description,
            vocabulary_type=entry.vocabulary_type,
            namespace_prefix=entry.namespace_prefix,
            namespace_uri=entry.namespace_uri,
            domain=entry.domain,
            status=entry.status or "candidate",
            review_status="under_review",
            version=1,
            created_by="standards_registry_service",
        )
        self._session.add(row)
        self._session.flush()
        return self._to_entry(row)

    def get_mappings_for_metric(
        self,
        metric_namespace: Optional[str] = None,
        *,
        metric_id: Optional[int] = None,
        allow_approved: bool = True,
        include_under_review: bool = False,
    ) -> StandardsLookupResult:
        """Return standards mappings for a resolved CIM metric.

        When ``allow_approved`` is False (candidate / unknown metrics), approved
        mappings are suppressed so we never claim standards alignment.
        """
        if self._session is None:
            return StandardsLookupResult(
                metric_namespace=metric_namespace,
                no_direct_standard_match=True,
                message="no session",
            )
        if not metric_namespace and metric_id is None:
            return StandardsLookupResult(
                no_direct_standard_match=True,
                message="no metric identity",
            )

        from cloud_metrics.models.cim_registry import (
            CimMetricDefinition,
            CimMetricMapping,
            CimStandard,
            CimStandardTerm,
        )

        metric = None
        if metric_id is not None:
            metric = self._session.get(CimMetricDefinition, metric_id)
        if metric is None and metric_namespace:
            metric = (
                self._session.query(CimMetricDefinition)
                .filter_by(namespace=metric_namespace)
                .first()
            )
        if metric is None:
            return StandardsLookupResult(
                metric_namespace=metric_namespace,
                no_direct_standard_match=True,
                message="metric not found",
            )

        # Candidate / non-approved metrics: do not attach approved standards
        metric_ok = (metric.status or "").lower() in _ACTIVE_METRIC
        if not allow_approved or not metric_ok:
            logger.info(
                "standards suppressed for non-approved metric: %s status=%s",
                metric.namespace,
                metric.status,
            )
            return StandardsLookupResult(
                metric_namespace=metric.namespace,
                no_direct_standard_match=True,
                message="approved standards not attached to candidate/unknown metrics",
            )

        statuses = set(_ACTIVE_MAPPING)
        if include_under_review:
            statuses |= {"candidate", "draft"}

        rows = (
            self._session.query(CimMetricMapping, CimStandard, CimStandardTerm)
            .join(CimStandard, CimMetricMapping.standard_id == CimStandard.id)
            .outerjoin(
                CimStandardTerm,
                CimMetricMapping.standard_term_id == CimStandardTerm.id,
            )
            .filter(
                CimMetricMapping.metric_id == metric.id,
                CimMetricMapping.standard_id.isnot(None),
                CimMetricMapping.status.in_(tuple(statuses)),
            )
            .all()
        )

        mappings: List[StandardMappingEntry] = []
        for map_row, std_row, term_row in rows:
            rel = map_row.relation_type or "underReview"
            mappings.append(
                StandardMappingEntry(
                    standard_code=std_row.code,
                    standard_name=std_row.name,
                    relation_type=rel,
                    confidence_score=float(map_row.confidence_score)
                    if map_row.confidence_score is not None
                    else 1.0,
                    review_status=map_row.review_status or "pending",
                    status=map_row.status or "draft",
                    notes=map_row.rationale or map_row.notes,
                    standard_term=(
                        (term_row.term_label or term_row.term_code) if term_row else None
                    ),
                    standard_term_code=term_row.term_code if term_row else None,
                    metric_namespace=metric.namespace,
                    mapping_id=map_row.id,
                    standard_id=std_row.id,
                )
            )

        has_exact = any(m.relation_type == "exactMatch" for m in mappings)
        # True when there is no exact identity claim (contextual/input still allowed)
        no_direct = not has_exact

        logger.info(
            "standards mappings for %s: %s (exact=%s)",
            metric.namespace,
            [(m.standard_code, m.relation_type) for m in mappings],
            has_exact,
        )

        return StandardsLookupResult(
            metric_namespace=metric.namespace,
            mappings=mappings,
            relation_types=[m.relation_type for m in mappings],
            confidence_scores=[m.confidence_score for m in mappings],
            review_statuses=[m.review_status for m in mappings],
            notes=[m.notes for m in mappings],
            no_direct_standard_match=no_direct,
            message=None if mappings else "no standards mappings seeded",
        )

    def _to_entry(self, row) -> StandardEntry:
        return StandardEntry(
            code=row.code,
            name=row.name,
            url=row.url,
            description=row.description,
            vocabulary_type=row.vocabulary_type,
            namespace_prefix=row.namespace_prefix,
            namespace_uri=row.namespace_uri,
            version=row.standard_version,
            domain=row.domain,
            status=row.status or "active",
            id=row.id,
        )


def get_standards_registry_service(
    session: Optional[Session] = None,
) -> StandardsRegistryService:
    return StandardsRegistryService(session=session)
