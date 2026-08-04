"""Source Registry service — CIM ``cim_sources`` (Milestone 6).

Without a session, keeps Milestone 1 skeleton behaviour (empty lists).
Legacy ``models.source.Source`` / API paths are unchanged.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Mapping, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from cloud_metrics.registry.base import RegistryName, SKELETON_ONLY
from cloud_metrics.registry.context_extract import (
    extract_source_hints,
    normalize_source_type,
)
from cloud_metrics.registry.source.types import SourceEntry, SourceResolutionResult

logger = logging.getLogger(__name__)

CREATED_BY = "milestone6_source_registry"


class SourceRegistryService:
    """Resolve / upsert sources in ``cim_sources`` when a session is provided."""

    registry_name = RegistryName.SOURCE
    skeleton_only = SKELETON_ONLY

    def __init__(self, session: Optional[Session] = None) -> None:
        self._session = session

    def list_entries(self) -> List[SourceEntry]:
        if self._session is None:
            return []
        from cloud_metrics.models.cim_registry import CimSource

        return [self._to_entry(r) for r in self._session.query(CimSource).all()]

    def get_by_name(
        self, name: str, *, source_type: Optional[str] = None
    ) -> Optional[SourceEntry]:
        if self._session is None:
            return None
        row = self._find(name, source_type=source_type)
        return self._to_entry(row) if row else None

    def get_by_id(self, source_id: int) -> Optional[SourceEntry]:
        if self._session is None:
            return None
        from cloud_metrics.models.cim_registry import CimSource

        row = self._session.get(CimSource, source_id)
        return self._to_entry(row) if row else None

    def register(self, entry: SourceEntry) -> SourceEntry:
        """Idempotent upsert by (name, type)."""
        if self._session is None:
            return entry
        result = self.resolve_or_create(
            name=entry.name,
            source_type=entry.type,
            metadata_info=entry.metadata,
            protocol=entry.protocol,
            format=entry.format,
            create_candidate=True,
            confidence=entry.confidence_score,
            notes=entry.notes,
        )
        return result.entry or entry

    def resolve_or_create(
        self,
        *,
        name: Optional[str],
        source_type: Optional[str] = None,
        metadata_info: Optional[Dict[str, Any]] = None,
        protocol: Optional[str] = None,
        format: Optional[str] = None,
        ingestion_method: Optional[str] = None,
        create_candidate: bool = True,
        confidence: Optional[float] = None,
        notes: Optional[str] = None,
    ) -> SourceResolutionResult:
        """Find existing source or optionally create a candidate."""
        if not name or not str(name).strip():
            return SourceResolutionResult(
                resolution_status="missing",
                message="No source name provided",
                warnings=["missing source name"],
            )

        if self._session is None:
            return SourceResolutionResult(
                source_name=name,
                source_type=normalize_source_type(source_type),
                resolution_status="unknown",
                message="No session; cannot resolve Source Registry",
                warnings=["no session"],
                confidence_score=confidence,
            )

        typ = normalize_source_type(source_type) or "manual_input"
        existing = self._find(name, source_type=typ)
        if existing is None and source_type is None:
            # Ambiguous: same name with multiple types
            matches = self._find_all_by_name(name)
            if len(matches) > 1:
                return SourceResolutionResult(
                    source_name=name,
                    resolution_status="ambiguous",
                    message=f"Multiple sources named '{name}'",
                    warnings=[f"ambiguous: {[m.type for m in matches]}"],
                    confidence_score=0.4,
                )
            if len(matches) == 1:
                existing = matches[0]

        if existing is not None:
            entry = self._to_entry(existing)
            logger.info(
                "source resolved: id=%s name=%s type=%s",
                existing.id,
                existing.name,
                existing.type,
            )
            return SourceResolutionResult(
                source_id=existing.id,
                source_name=existing.name,
                source_type=existing.type,
                resolution_status="resolved",
                confidence_score=float(
                    existing.confidence_score
                    if existing.confidence_score is not None
                    else 1.0
                ),
                message="existing source",
                entry=entry,
            )

        if not create_candidate:
            return SourceResolutionResult(
                source_name=name,
                source_type=typ,
                resolution_status="missing",
                message=f"Source '{name}' not found",
                warnings=["source not found"],
                confidence_score=confidence,
            )

        meta = dict(metadata_info or {})
        if ingestion_method:
            meta.setdefault("ingestion_method", ingestion_method)

        from cloud_metrics.models.cim_registry import CimSource

        row = CimSource(
            name=str(name).strip(),
            type=typ,
            protocol=protocol,
            format=format,
            capabilities={},
            auth_method="none",
            metadata_info=meta,
            status="candidate",
            review_status="under_review",
            confidence_score=confidence if confidence is not None else 0.7,
            version=1,
            created_by=CREATED_BY,
            notes=notes or "Candidate source created during Milestone 6 resolution",
        )
        self._session.add(row)
        self._session.flush()
        logger.info(
            "source candidate created: id=%s name=%s type=%s",
            row.id,
            row.name,
            row.type,
        )
        entry = self._to_entry(row)
        return SourceResolutionResult(
            source_id=row.id,
            source_name=row.name,
            source_type=row.type,
            resolution_status="candidate_created",
            confidence_score=float(row.confidence_score or 0.7),
            message="candidate source created",
            entry=entry,
        )

    def resolve_from_metadata(
        self,
        metadata: Optional[Mapping[str, Any]],
        *,
        create_candidate: bool = True,
    ) -> SourceResolutionResult:
        hints = extract_source_hints(metadata)
        if not hints.name:
            return SourceResolutionResult(
                resolution_status="missing",
                message="Could not extract source from metadata",
                warnings=["no source hints"],
            )
        return self.resolve_or_create(
            name=hints.name,
            source_type=hints.type,
            metadata_info=hints.metadata,
            ingestion_method=hints.ingestion_method,
            create_candidate=create_candidate,
            confidence=hints.confidence,
        )

    # ------------------------------------------------------------------

    def _find(self, name: str, *, source_type: Optional[str] = None):
        assert self._session is not None
        from cloud_metrics.models.cim_registry import CimSource

        q = self._session.query(CimSource).filter(
            func.lower(CimSource.name) == name.strip().lower()
        )
        if source_type:
            q = q.filter(func.lower(CimSource.type) == source_type.strip().lower())
        return q.first()

    def _find_all_by_name(self, name: str):
        assert self._session is not None
        from cloud_metrics.models.cim_registry import CimSource

        return (
            self._session.query(CimSource)
            .filter(func.lower(CimSource.name) == name.strip().lower())
            .all()
        )

    def _to_entry(self, row) -> SourceEntry:
        return SourceEntry(
            id=row.id,
            name=row.name,
            type=row.type,
            protocol=row.protocol,
            format=row.format,
            schema_version=row.schema_version,
            capabilities=row.capabilities or {},
            auth_method=row.auth_method or "none",
            status=row.status,
            review_status=row.review_status,
            confidence_score=row.confidence_score,
            version=row.version or 1,
            notes=row.notes,
            metadata=row.metadata_info or {},
            created_at=row.created_at,
            updated_at=row.updated_at,
        )


def get_source_registry_service(
    session: Optional[Session] = None,
) -> SourceRegistryService:
    return SourceRegistryService(session=session)
