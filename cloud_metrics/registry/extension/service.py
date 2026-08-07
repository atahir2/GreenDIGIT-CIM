"""Extension Registry service — Milestone 9.

Creates / looks up extension candidates for unknown metrics.
Never auto-approves.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from cloud_metrics.registry.base import RegistryName, SKELETON_ONLY
from cloud_metrics.registry.extension.types import ExtensionEntry

logger = logging.getLogger(__name__)

_WORD = re.compile(r"[a-zA-Z0-9]+")


def suggest_extension_namespace(raw_metric_name: str) -> str:
    parts = _WORD.findall((raw_metric_name or "").lower())
    slug = "_".join(parts) or "unknown"
    if len(slug) > 120:
        slug = slug[:120]
    return f"cim:extension.{slug}"


class ExtensionRegistryService:
    """Extension Registry with optional DB session."""

    registry_name = RegistryName.EXTENSION
    skeleton_only = SKELETON_ONLY

    def __init__(self, session: Optional[Session] = None) -> None:
        self._session = session

    def list_entries(self) -> list[ExtensionEntry]:
        if self._session is None:
            return []
        from cloud_metrics.models.cim_registry import CimExtensionMetric

        rows = self._session.query(CimExtensionMetric).all()
        return [self._to_entry(r) for r in rows]

    def get_by_id(self, extension_id: int) -> Optional[ExtensionEntry]:
        if self._session is None:
            return None
        from cloud_metrics.models.cim_registry import CimExtensionMetric

        row = self._session.get(CimExtensionMetric, extension_id)
        return self._to_entry(row) if row else None

    def find_by_raw_key(self, raw_metric_name: str) -> Optional[ExtensionEntry]:
        if self._session is None or not raw_metric_name:
            return None
        from cloud_metrics.models.cim_registry import (
            CimExtensionMetric,
            CimMetricDefinition,
        )

        ns = suggest_extension_namespace(raw_metric_name)
        metric = (
            self._session.query(CimMetricDefinition)
            .filter_by(namespace=ns)
            .first()
        )
        if metric is None:
            # notes may contain raw key
            metric = (
                self._session.query(CimMetricDefinition)
                .filter(
                    CimMetricDefinition.notes.isnot(None),
                    CimMetricDefinition.notes.contains(raw_metric_name),
                    CimMetricDefinition.namespace.like("cim:extension.%"),
                )
                .first()
            )
        if metric is None:
            return None
        ext = (
            self._session.query(CimExtensionMetric)
            .filter_by(metric_id=metric.id)
            .first()
        )
        return self._to_entry(ext) if ext else None

    def propose(self, entry: ExtensionEntry) -> ExtensionEntry:
        """Create or return existing extension candidate (never approved)."""
        if self._session is None:
            entry.status = entry.status or "candidate"
            entry.review_status = entry.review_status or "under_review"
            return entry

        raw = entry.raw_metric_name or ""
        existing = self.find_by_raw_key(raw) if raw else None
        if existing is not None:
            logger.info(
                "extension candidate dedup hit: raw=%s id=%s",
                raw,
                existing.id,
            )
            return existing

        from cloud_metrics.models.cim_registry import (
            CimExtensionMetric,
            CimMetricDefinition,
        )

        ns = entry.metric_namespace or suggest_extension_namespace(raw or "unknown")
        metric = (
            self._session.query(CimMetricDefinition)
            .filter_by(namespace=ns)
            .first()
        )
        if metric is None:
            metric = CimMetricDefinition(
                namespace=ns,
                label=raw or ns,
                description=entry.suggested_definition
                or f"Extension candidate for raw metric '{raw}'",
                domain=entry.suggested_domain or "extension",
                category=entry.suggested_category or "extension",
                metric_type="extension",
                status="candidate",
                review_status="under_review",
                confidence_score=entry.confidence_score,
                version=1,
                created_by=entry.proposed_by or "extension_registry",
                notes=f"raw_metric_name={raw}",
                tags=["extension", "candidate"],
            )
            self._session.add(metric)
            self._session.flush()

        now = datetime.now(timezone.utc)
        row = CimExtensionMetric(
            metric_id=metric.id,
            proposed_standard=entry.proposed_standard,
            justification=entry.justification
            or "Placeholder justification pending review",
            proposed_by=entry.proposed_by or "registry_orchestrator",
            proposed_at=entry.proposed_at or now,
            status="candidate",
            review_status="under_review",
            confidence_score=entry.confidence_score,
            version=1,
            created_by=entry.proposed_by or "extension_registry",
            notes=self._notes_blob(entry, raw),
        )
        self._session.add(row)
        self._session.flush()
        logger.info(
            "extension candidate created: raw=%s ns=%s id=%s",
            raw,
            ns,
            row.id,
        )
        return self._to_entry(row)

    def propose_from_raw(
        self,
        raw_metric_name: str,
        *,
        source_context: Optional[Dict[str, Any]] = None,
        suggested_unit: Optional[str] = None,
        confidence_score: Optional[float] = None,
        justification: Optional[str] = None,
    ) -> ExtensionEntry:
        return self.propose(
            ExtensionEntry(
                raw_metric_name=raw_metric_name,
                metric_namespace=suggest_extension_namespace(raw_metric_name),
                source_context=source_context,
                suggested_unit=suggested_unit,
                confidence_score=confidence_score,
                justification=justification
                or "Unknown/unresolved metric during orchestration",
                status="candidate",
                review_status="under_review",
                proposed_by="registry_orchestrator",
            )
        )

    def approve(self, extension_id: int) -> Optional[ExtensionEntry]:
        """Placeholder: set accepted/under_review — does not silently approve metric."""
        return self._set_status(
            extension_id,
            status="accepted",
            review_status="under_review",
            note="Marked accepted; metric remains candidate until catalogue promotion",
        )

    def reject(self, extension_id: int) -> Optional[ExtensionEntry]:
        return self._set_status(
            extension_id, status="rejected", review_status="rejected"
        )

    def merge(self, extension_id: int, target_namespace: str) -> Optional[ExtensionEntry]:
        """Placeholder merge: notes target namespace; does not auto-approve."""
        entry = self.get_by_id(extension_id)
        if entry is None or self._session is None:
            return entry
        from cloud_metrics.models.cim_registry import CimExtensionMetric

        row = self._session.get(CimExtensionMetric, extension_id)
        if row is None:
            return None
        row.status = "merged"
        row.review_status = "under_review"
        row.notes = (row.notes or "") + f"\nmerged_into={target_namespace}"
        self._session.flush()
        return self._to_entry(row)

    def update(self, extension_id: int, **fields: Any) -> Optional[ExtensionEntry]:
        if self._session is None:
            return None
        from cloud_metrics.models.cim_registry import CimExtensionMetric

        row = self._session.get(CimExtensionMetric, extension_id)
        if row is None:
            return None
        for key in ("justification", "proposed_standard", "proposed_by"):
            if key in fields and fields[key] is not None:
                setattr(row, key, fields[key])
        self._session.flush()
        return self._to_entry(row)

    def _set_status(
        self,
        extension_id: int,
        *,
        status: str,
        review_status: str,
        note: Optional[str] = None,
    ) -> Optional[ExtensionEntry]:
        if self._session is None:
            return None
        from cloud_metrics.models.cim_registry import CimExtensionMetric

        row = self._session.get(CimExtensionMetric, extension_id)
        if row is None:
            return None
        row.status = status
        row.review_status = review_status
        if note:
            row.notes = ((row.notes or "") + "\n" + note).strip()
        self._session.flush()
        return self._to_entry(row)

    def _notes_blob(self, entry: ExtensionEntry, raw: str) -> str:
        parts = [f"raw_metric_name={raw}"]
        if entry.suggested_unit:
            parts.append(f"suggested_unit={entry.suggested_unit}")
        if entry.suggested_domain:
            parts.append(f"suggested_domain={entry.suggested_domain}")
        if entry.suggested_category:
            parts.append(f"suggested_category={entry.suggested_category}")
        if entry.suggested_quantity_kind:
            parts.append(f"suggested_quantity_kind={entry.suggested_quantity_kind}")
        if entry.source_context:
            parts.append(f"source_context={entry.source_context}")
        return "; ".join(parts)

    def _to_entry(self, row) -> ExtensionEntry:
        metric = getattr(row, "metric", None)
        notes = row.notes or ""
        raw = None
        for part in notes.split(";"):
            part = part.strip()
            if part.startswith("raw_metric_name="):
                raw = part.split("=", 1)[1]
                break
        return ExtensionEntry(
            metric_namespace=metric.namespace if metric is not None else None,
            metric_id=row.metric_id,
            raw_metric_name=raw,
            proposed_standard=row.proposed_standard,
            justification=row.justification,
            confidence_score=row.confidence_score,
            status=row.status or "candidate",
            review_status=row.review_status or "under_review",
            proposed_by=row.proposed_by,
            proposed_at=row.proposed_at,
            id=row.id,
            extra={"notes": notes} if notes else {},
        )


def get_extension_registry_service(
    session: Optional[Session] = None,
) -> ExtensionRegistryService:
    return ExtensionRegistryService(session=session)
