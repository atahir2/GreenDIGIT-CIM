"""Provenance Registry service — Milestone 9 (CIM ``cim_provenance_records``)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from cloud_metrics.registry.base import RegistryName, SKELETON_ONLY
from cloud_metrics.registry.provenance.types import ProvenanceEntry

logger = logging.getLogger(__name__)


class ProvenanceRegistryService:
    """Provenance Registry with optional DB session (CIM tables)."""

    registry_name = RegistryName.PROVENANCE
    skeleton_only = SKELETON_ONLY

    def __init__(self, session: Optional[Session] = None) -> None:
        self._session = session

    def list_entries(self) -> List[ProvenanceEntry]:
        if self._session is None:
            return []
        from cloud_metrics.models.cim_registry import CimProvenanceRecord

        rows = (
            self._session.query(CimProvenanceRecord)
            .order_by(CimProvenanceRecord.id.desc())
            .limit(200)
            .all()
        )
        return [self._to_entry(r) for r in rows]

    def record(self, entry: ProvenanceEntry) -> ProvenanceEntry:
        """Persist a provenance activity. Echoes when no session."""
        if self._session is None:
            return entry
        from cloud_metrics.models.cim_registry import CimProvenanceRecord

        now = datetime.now(timezone.utc)
        row = CimProvenanceRecord(
            entity_type=entry.entity_type,
            entity_id=entry.entity_id,
            activity=entry.activity,
            agent=entry.agent,
            started_at=entry.started_at or now,
            ended_at=entry.ended_at or now,
            inputs=entry.inputs or {},
            outputs=entry.outputs or {},
            method=entry.method,
            prov_uri=entry.prov_uri,
            confidence_score=entry.confidence,
            status=entry.status or "approved",
            review_status="approved",
            notes=entry.notes,
            version=1,
            created_by=entry.agent,
        )
        self._session.add(row)
        self._session.flush()
        logger.info(
            "provenance recorded: activity=%s entity=%s/%s id=%s",
            entry.activity,
            entry.entity_type,
            entry.entity_id,
            row.id,
        )
        return self._to_entry(row)

    def record_activity(
        self,
        *,
        entity_type: str,
        activity: str,
        agent: str = "registry_orchestrator",
        entity_id: Optional[int] = None,
        inputs: Optional[Dict[str, Any]] = None,
        outputs: Optional[Dict[str, Any]] = None,
        method: Optional[str] = None,
        confidence: Optional[float] = None,
        notes: Optional[str] = None,
        status: str = "approved",
    ) -> ProvenanceEntry:
        return self.record(
            ProvenanceEntry(
                entity_type=entity_type,
                entity_id=entity_id,
                activity=activity,
                agent=agent,
                inputs=inputs or {},
                outputs=outputs or {},
                method=method,
                confidence=confidence,
                notes=notes,
                status=status,
            )
        )

    def get_chain(
        self, entity_type: str, entity_id: int
    ) -> List[ProvenanceEntry]:
        if self._session is None:
            return []
        from cloud_metrics.models.cim_registry import CimProvenanceRecord

        rows = (
            self._session.query(CimProvenanceRecord)
            .filter_by(entity_type=entity_type, entity_id=entity_id)
            .order_by(CimProvenanceRecord.id.asc())
            .all()
        )
        return [self._to_entry(r) for r in rows]

    def _to_entry(self, row) -> ProvenanceEntry:
        return ProvenanceEntry(
            entity_type=row.entity_type,
            entity_id=row.entity_id,
            activity=row.activity,
            agent=row.agent,
            started_at=row.started_at,
            ended_at=row.ended_at,
            inputs=dict(row.inputs or {}),
            outputs=dict(row.outputs or {}),
            method=row.method,
            confidence=row.confidence_score,
            status=row.status or "approved",
            notes=row.notes,
            prov_uri=row.prov_uri,
            id=row.id,
            created_at=row.created_at,
        )


def get_provenance_registry_service(
    session: Optional[Session] = None,
) -> ProvenanceRegistryService:
    return ProvenanceRegistryService(session=session)
