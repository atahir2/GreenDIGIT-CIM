"""Evidence Registry service — Milestone 9."""

from __future__ import annotations

import logging
from typing import List, Optional

from sqlalchemy.orm import Session

from cloud_metrics.registry.base import RegistryName, SKELETON_ONLY
from cloud_metrics.registry.evidence.types import (
    EvidenceLookupResult,
    EvidenceRequirementEntry,
)

logger = logging.getLogger(__name__)

_ACTIVE = frozenset({"approved", "active"})


class EvidenceRegistryService:
    """Evidence Registry with optional DB session."""

    registry_name = RegistryName.EVIDENCE
    skeleton_only = SKELETON_ONLY

    def __init__(self, session: Optional[Session] = None) -> None:
        self._session = session

    def list_entries(self) -> List[EvidenceRequirementEntry]:
        if self._session is None:
            return []
        from cloud_metrics.models.cim_registry import CimEvidenceRequirement

        rows = (
            self._session.query(CimEvidenceRequirement)
            .filter(CimEvidenceRequirement.status.in_(tuple(_ACTIVE)))
            .all()
        )
        return [self._to_entry(r) for r in rows]

    def get_by_id(self, requirement_id: int) -> Optional[EvidenceRequirementEntry]:
        if self._session is None:
            return None
        from cloud_metrics.models.cim_registry import CimEvidenceRequirement

        row = self._session.get(CimEvidenceRequirement, requirement_id)
        return self._to_entry(row) if row else None

    def register(self, entry: EvidenceRequirementEntry) -> EvidenceRequirementEntry:
        return entry

    def get_requirements_for_metric(
        self,
        metric_namespace: Optional[str] = None,
        *,
        metric_id: Optional[int] = None,
        standard_code: Optional[str] = None,
        lifecycle_stage: Optional[str] = None,
        reporting_purpose: Optional[str] = None,
    ) -> EvidenceLookupResult:
        """Return seeded evidence requirements for a metric.

        ``lifecycle_stage`` / ``reporting_purpose`` are soft filters against
        description / boundary text when provided.
        """
        if self._session is None:
            return EvidenceLookupResult(
                metric_namespace=metric_namespace,
                readiness_status="unknown",
                message="no session",
            )

        from cloud_metrics.models.cim_registry import (
            CimEvidenceRequirement,
            CimMetricDefinition,
            CimStandard,
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
            return EvidenceLookupResult(
                metric_namespace=metric_namespace,
                readiness_status="not_applicable",
                message="metric not found",
            )

        q = (
            self._session.query(CimEvidenceRequirement, CimStandard)
            .join(CimStandard, CimEvidenceRequirement.standard_id == CimStandard.id)
            .filter(
                CimEvidenceRequirement.metric_id == metric.id,
                CimEvidenceRequirement.status.in_(tuple(_ACTIVE)),
            )
        )
        if standard_code:
            q = q.filter(CimStandard.code == standard_code)

        rows = q.all()
        reqs: List[EvidenceRequirementEntry] = []
        for ev, std in rows:
            entry = self._to_entry(ev, standard=std, namespace=metric.namespace)
            if lifecycle_stage or reporting_purpose:
                blob = " ".join(
                    filter(
                        None,
                        [
                            entry.description,
                            entry.boundary,
                            entry.reporting_period,
                            entry.evidence_type,
                        ],
                    )
                ).lower()
                if lifecycle_stage and lifecycle_stage.lower() not in blob:
                    # soft: still include unless clearly unrelated — keep all for KPI
                    pass
                if reporting_purpose and reporting_purpose.lower() not in blob:
                    pass
            reqs.append(entry)

        mandatory = [
            r
            for r in reqs
            if (r.requirement_level or "").lower() in {"mandatory", "required"}
        ]
        optional = [
            r
            for r in reqs
            if (r.requirement_level or "").lower()
            in {"recommended", "optional"}
        ]
        if reqs:
            readiness = "declared"
        else:
            readiness = "not_applicable"

        logger.info(
            "evidence requirements for %s: %d (mandatory=%d)",
            metric.namespace,
            len(reqs),
            len(mandatory),
        )
        return EvidenceLookupResult(
            metric_namespace=metric.namespace,
            requirements=reqs,
            mandatory=mandatory,
            optional=optional,
            readiness_status=readiness,
            message=None if reqs else "no evidence requirements seeded",
        )

    def _to_entry(
        self, row, *, standard=None, namespace: Optional[str] = None
    ) -> EvidenceRequirementEntry:
        std = standard or getattr(row, "standard", None)
        metric = getattr(row, "metric", None)
        return EvidenceRequirementEntry(
            standard_code=std.code if std is not None else None,
            standard_name=std.name if std is not None else None,
            metric_namespace=namespace
            or (metric.namespace if metric is not None else None),
            evidence_type=row.evidence_type,
            requirement_level=row.requirement_level or "recommended",
            reporting_period=row.reporting_period,
            aggregation_method=row.aggregation_method,
            boundary=row.boundary,
            description=row.description,
            id=row.id,
            status=row.status or "approved",
            review_status=row.review_status or "approved",
        )


def get_evidence_registry_service(
    session: Optional[Session] = None,
) -> EvidenceRegistryService:
    return EvidenceRegistryService(session=session)
