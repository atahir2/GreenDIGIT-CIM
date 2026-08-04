"""Lifecycle Registry service — Milestone 8.

Retrieves seeded metric↔lifecycle links. Does not invent stages.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from sqlalchemy.orm import Session

from cloud_metrics.registry.base import RegistryName, SKELETON_ONLY
from cloud_metrics.registry.lifecycle.types import (
    RELEVANCE_TO_IMPORTANCE,
    STAGE_USAGE_PURPOSE,
    LifecycleLookupResult,
    LifecycleStageEntry,
    MetricLifecycleLink,
)

logger = logging.getLogger(__name__)

_ACTIVE = frozenset({"approved", "active", "candidate"})


class LifecycleRegistryService:
    """Lifecycle Registry with optional DB session."""

    registry_name = RegistryName.LIFECYCLE
    skeleton_only = SKELETON_ONLY

    def __init__(self, session: Optional[Session] = None) -> None:
        self._session = session

    def list_entries(self) -> List[LifecycleStageEntry]:
        if self._session is None:
            return []
        from cloud_metrics.models.cim_registry import CimLifecycleStage

        rows = (
            self._session.query(CimLifecycleStage)
            .order_by(CimLifecycleStage.sequence.asc())
            .all()
        )
        return [self._to_stage(r) for r in rows]

    def get_by_stage(self, stage: str) -> Optional[LifecycleStageEntry]:
        if self._session is None or not stage:
            return None
        from cloud_metrics.models.cim_registry import CimLifecycleStage

        key = stage.strip().lower()
        row = (
            self._session.query(CimLifecycleStage)
            .filter(CimLifecycleStage.stage_key == key)
            .first()
        )
        if row is None:
            row = (
                self._session.query(CimLifecycleStage)
                .filter(CimLifecycleStage.name == stage.strip())
                .first()
            )
        return self._to_stage(row) if row else None

    def link_metric(self, stage: str, metric_namespace: str) -> None:
        """No-op inventing disabled — links come from seed/migration only."""
        logger.info(
            "link_metric ignored (seed-only policy): stage=%s metric=%s",
            stage,
            metric_namespace,
        )
        return None

    def get_links_for_metric(
        self,
        metric_namespace: Optional[str] = None,
        *,
        metric_id: Optional[int] = None,
        include_candidate_links: bool = True,
    ) -> LifecycleLookupResult:
        """Return lifecycle links for a metric. Empty if none seeded."""
        if self._session is None:
            return LifecycleLookupResult(
                metric_namespace=metric_namespace,
                message="no session",
            )
        if not metric_namespace and metric_id is None:
            return LifecycleLookupResult(message="no metric identity")

        from cloud_metrics.models.cim_registry import (
            CimLifecycleStage,
            CimMetricDefinition,
            CimMetricLifecycleLink,
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
            return LifecycleLookupResult(
                metric_namespace=metric_namespace,
                message="metric not found",
            )

        q = (
            self._session.query(CimMetricLifecycleLink, CimLifecycleStage)
            .join(
                CimLifecycleStage,
                CimMetricLifecycleLink.lifecycle_stage_id == CimLifecycleStage.id,
            )
            .filter(CimMetricLifecycleLink.metric_id == metric.id)
        )
        if not include_candidate_links:
            q = q.filter(CimMetricLifecycleLink.status.in_(("approved", "active")))
        else:
            q = q.filter(CimMetricLifecycleLink.status.in_(tuple(_ACTIVE)))

        rows = q.order_by(CimLifecycleStage.sequence.asc()).all()
        links: List[MetricLifecycleLink] = []
        for link_row, stage_row in rows:
            relevance = (link_row.relevance or "secondary").lower()
            importance = RELEVANCE_TO_IMPORTANCE.get(relevance, "recommended")
            purpose = STAGE_USAGE_PURPOSE.get(
                stage_row.stage_key, stage_row.stage_key
            )
            links.append(
                MetricLifecycleLink(
                    stage_key=stage_row.stage_key,
                    stage_label=stage_row.label or stage_row.name,
                    usage_purpose=purpose,
                    importance=importance,
                    relevance=relevance,
                    review_status=link_row.review_status or "pending",
                    status=link_row.status or "draft",
                    notes=link_row.notes,
                    lifecycle_stage_id=stage_row.id,
                    metric_id=metric.id,
                    metric_namespace=metric.namespace,
                )
            )

        logger.info(
            "lifecycle links for %s: %s",
            metric.namespace,
            [lnk.stage_key for lnk in links],
        )
        return LifecycleLookupResult(
            metric_namespace=metric.namespace,
            links=links,
            stages=[lnk.stage_key for lnk in links],
            usage_purposes=[lnk.usage_purpose or "" for lnk in links],
            importance=[lnk.importance for lnk in links],
            review_statuses=[lnk.review_status for lnk in links],
            message=None if links else "no lifecycle links seeded",
        )

    def _to_stage(self, row) -> LifecycleStageEntry:
        return LifecycleStageEntry(
            stage=row.stage_key,
            label=row.label or row.name,
            description=row.description,
            sequence=row.sequence,
            id=row.id,
            status=row.status or "approved",
            review_status=row.review_status or "approved",
        )


def get_lifecycle_registry_service(
    session: Optional[Session] = None,
) -> LifecycleRegistryService:
    return LifecycleRegistryService(session=session)
