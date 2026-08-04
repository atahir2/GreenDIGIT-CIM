"""Asset Registry service — CIM ``cim_assets`` (Milestone 6).

Supports optional parent/child hierarchy when metadata provides both sides.
Does not invent hierarchy links from missing data.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Mapping, Optional, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from cloud_metrics.registry.asset.types import (
    ASSET_TYPES,
    AssetEntry,
    AssetResolutionResult,
)
from cloud_metrics.registry.base import RegistryName, SKELETON_ONLY
from cloud_metrics.registry.context_extract import AssetHints, extract_asset_hints

logger = logging.getLogger(__name__)

CREATED_BY = "milestone6_asset_registry"


class AssetRegistryService:
    """Resolve / upsert assets in ``cim_assets`` when a session is provided."""

    registry_name = RegistryName.ASSET
    skeleton_only = SKELETON_ONLY

    def __init__(self, session: Optional[Session] = None) -> None:
        self._session = session

    def list_entries(self) -> List[AssetEntry]:
        if self._session is None:
            return []
        from cloud_metrics.models.cim_registry import CimAsset

        return [self._to_entry(r) for r in self._session.query(CimAsset).all()]

    def get_by_id(self, asset_id: int) -> Optional[AssetEntry]:
        if self._session is None:
            return None
        from cloud_metrics.models.cim_registry import CimAsset

        row = self._session.get(CimAsset, asset_id)
        return self._to_entry(row) if row else None

    def get_by_identifier(
        self, identifier: str, *, asset_type: Optional[str] = None
    ) -> Optional[AssetEntry]:
        if self._session is None:
            return None
        row = self._find(identifier, asset_type=asset_type)
        return self._to_entry(row) if row else None

    def get_hierarchy(self, asset_id: int) -> List[AssetEntry]:
        """Walk parents from leaf → root, then reverse to root → leaf."""
        entry = self.get_by_id(asset_id)
        if entry is None:
            return []
        chain = [entry]
        seen = {asset_id}
        current = entry
        while current.parent_id and current.parent_id not in seen:
            parent = self.get_by_id(current.parent_id)
            if parent is None:
                break
            seen.add(parent.id or -1)
            chain.append(parent)
            current = parent
        chain.reverse()
        return chain

    def register(self, entry: AssetEntry) -> AssetEntry:
        if self._session is None:
            return entry
        result = self.resolve_or_create(
            identifier=entry.identifier or entry.name,
            asset_type=entry.type,
            name=entry.name,
            parent_id=entry.parent_id,
            create_candidate=True,
            confidence=entry.confidence_score,
            notes=entry.notes,
            specifications=entry.specifications,
            location=entry.location,
            provider=entry.provider,
        )
        return result.entry or entry

    def resolve_or_create(
        self,
        *,
        identifier: Optional[str],
        asset_type: Optional[str],
        name: Optional[str] = None,
        parent_id: Optional[int] = None,
        create_candidate: bool = True,
        confidence: Optional[float] = None,
        notes: Optional[str] = None,
        specifications: Optional[Dict[str, Any]] = None,
        location: Optional[str] = None,
        provider: Optional[str] = None,
    ) -> AssetResolutionResult:
        if not identifier or not str(identifier).strip():
            return AssetResolutionResult(
                resolution_status="missing",
                message="No asset identifier provided",
                warnings=["missing asset identifier"],
            )
        if not asset_type:
            return AssetResolutionResult(
                asset_identifier=identifier,
                resolution_status="missing",
                message="No asset type provided",
                warnings=["missing asset type"],
            )

        typ = self._normalize_type(asset_type)
        if self._session is None:
            return AssetResolutionResult(
                asset_identifier=identifier,
                asset_type=typ,
                resolution_status="unknown",
                message="No session; cannot resolve Asset Registry",
                warnings=["no session"],
                confidence_score=confidence,
            )

        existing = self._find(identifier, asset_type=typ)
        if existing is not None:
            # Optionally attach parent if missing and provided
            if parent_id and not existing.parent_id:
                existing.parent_id = parent_id
                self._session.flush()
            entry = self._to_entry(existing)
            logger.info(
                "asset resolved: id=%s identifier=%s type=%s",
                existing.id,
                existing.identifier,
                existing.type,
            )
            return AssetResolutionResult(
                asset_id=existing.id,
                asset_identifier=existing.identifier,
                asset_type=existing.type,
                parent_asset_id=existing.parent_id,
                resolution_status="resolved",
                confidence_score=float(
                    existing.confidence_score
                    if existing.confidence_score is not None
                    else 1.0
                ),
                message="existing asset",
                entry=entry,
            )

        if not create_candidate:
            return AssetResolutionResult(
                asset_identifier=identifier,
                asset_type=typ,
                resolution_status="missing",
                message=f"Asset '{identifier}' ({typ}) not found",
                warnings=["asset not found"],
                confidence_score=confidence,
            )

        from cloud_metrics.models.cim_registry import CimAsset

        row = CimAsset(
            identifier=str(identifier).strip(),
            name=(name or str(identifier)).strip(),
            type=typ,
            parent_id=parent_id,
            location=location,
            provider=provider,
            specifications=specifications or {},
            status="candidate",
            review_status="under_review",
            confidence_score=confidence if confidence is not None else 0.7,
            version=1,
            created_by=CREATED_BY,
            notes=notes or "Candidate asset created during Milestone 6 resolution",
        )
        self._session.add(row)
        self._session.flush()
        logger.info(
            "asset candidate created: id=%s identifier=%s type=%s parent=%s",
            row.id,
            row.identifier,
            row.type,
            row.parent_id,
        )
        entry = self._to_entry(row)
        return AssetResolutionResult(
            asset_id=row.id,
            asset_identifier=row.identifier,
            asset_type=row.type,
            parent_asset_id=row.parent_id,
            resolution_status="candidate_created",
            confidence_score=float(row.confidence_score or 0.7),
            message="candidate asset created",
            entry=entry,
        )

    def resolve_from_metadata(
        self,
        metadata: Optional[Mapping[str, Any]],
        *,
        create_candidate: bool = True,
        build_hierarchy: bool = True,
    ) -> AssetResolutionResult:
        """Resolve primary asset; optionally create parent chain from hints."""
        hints = extract_asset_hints(metadata)
        if not hints.primary_identifier or not hints.primary_type:
            return AssetResolutionResult(
                resolution_status="missing",
                message="Could not extract asset from metadata",
                warnings=["no asset hints"],
            )

        hierarchy_entries: List[AssetEntry] = []
        warnings: List[str] = []
        parent_id: Optional[int] = None

        if build_hierarchy:
            parent_id, hierarchy_entries, warnings = self._ensure_hierarchy(
                hints, create_candidate=create_candidate
            )

        # If hierarchy walk already produced the primary leaf, return it.
        norm_primary = self._normalize_type(hints.primary_type)
        for e in hierarchy_entries:
            if (
                e.identifier
                and e.identifier.lower() == hints.primary_identifier.lower()
                and e.type == norm_primary
            ):
                status = (
                    "resolved"
                    if e.status in {"approved", "active"}
                    else "candidate_created"
                )
                return AssetResolutionResult(
                    asset_id=e.id,
                    asset_identifier=e.identifier,
                    asset_type=e.type,
                    parent_asset_id=e.parent_id,
                    resolution_status=status,
                    confidence_score=e.confidence_score,
                    message="asset resolved via hierarchy enrichment",
                    entry=e,
                    hierarchy=list(hierarchy_entries),
                    warnings=warnings,
                )

        # Primary not in hierarchy chain (e.g. build_hierarchy=False)
        primary = self.resolve_or_create(
            identifier=hints.primary_identifier,
            asset_type=hints.primary_type,
            name=hints.primary_identifier,
            parent_id=parent_id,
            create_candidate=create_candidate,
            confidence=hints.confidence,
            specifications={"extracted_from": "metadata"},
        )
        primary.hierarchy = hierarchy_entries
        primary.warnings.extend(warnings)
        return primary

    # ------------------------------------------------------------------

    def _ensure_hierarchy(
        self, hints: AssetHints, *, create_candidate: bool
    ) -> Tuple[Optional[int], List[AssetEntry], List[str]]:
        """Create/link assets along known hint fields. Returns leaf parent_id."""
        warnings: List[str] = []
        entries: List[AssetEntry] = []
        parent_id: Optional[int] = None

        # Explicit chains we support when both ends exist in hints
        infra = [
            (hints.site, "site"),
            (hints.data_centre, "data_centre"),
            (hints.cluster, "cluster"),
            (hints.rack, "rack"),
            (hints.node, "node"),
            (hints.server, "server"),
            (hints.gpu, "gpu"),
            (hints.cpu, "cpu"),
            (hints.virtual_machine, "virtual_machine"),
            (hints.container, "container"),
            (hints.service, "service"),
        ]
        research = [
            (hints.workflow, "workflow"),
            (hints.workflow_run, "workflow_run"),
            (hints.dataset, "dataset"),
            (hints.experiment, "experiment"),
        ]

        def walk(steps: List[Tuple[Optional[str], str]]) -> Optional[int]:
            nonlocal warnings, entries
            pid: Optional[int] = None
            for ident, typ in steps:
                if not ident:
                    continue
                res = self.resolve_or_create(
                    identifier=ident,
                    asset_type=typ,
                    name=ident,
                    parent_id=pid,
                    create_candidate=create_candidate,
                    confidence=hints.confidence,
                )
                if res.resolution_status in {"missing", "unknown", "ambiguous"}:
                    warnings.append(res.message or f"skipped {typ}:{ident}")
                    continue
                if res.entry:
                    entries.append(res.entry)
                pid = res.asset_id
            return pid

        leaf_infra = walk(infra)
        leaf_research = walk(research)

        # Prefer most specific parent for the primary leaf
        if hints.primary_type in {
            "gpu",
            "cpu",
            "virtual_machine",
            "container",
            "service",
            "node",
            "server",
            "rack",
            "cluster",
            "data_centre",
            "site",
        }:
            return leaf_infra, entries, warnings
        if hints.primary_type in {
            "workflow",
            "workflow_run",
            "dataset",
            "experiment",
        }:
            return leaf_research, entries, warnings
        return leaf_infra or leaf_research, entries, warnings

    def _normalize_type(self, asset_type: str) -> str:
        t = asset_type.strip().lower().replace("-", "_").replace(" ", "_")
        aliases = {
            "datacenter": "data_centre",
            "data_center": "data_centre",
            "dc": "data_centre",
            "vm": "virtual_machine",
            "host": "node",
            "hostname": "node",
        }
        t = aliases.get(t, t)
        if t not in ASSET_TYPES and t not in {
            "data_centre",
            "virtual_machine",
            "workflow_run",
        }:
            # still allow custom types as candidates
            pass
        return t

    def _find(self, identifier: str, *, asset_type: Optional[str] = None):
        assert self._session is not None
        from cloud_metrics.models.cim_registry import CimAsset

        q = self._session.query(CimAsset).filter(
            func.lower(CimAsset.identifier) == identifier.strip().lower()
        )
        if asset_type:
            q = q.filter(
                func.lower(CimAsset.type) == self._normalize_type(asset_type).lower()
            )
        return q.first()

    def _to_entry(self, row) -> AssetEntry:
        return AssetEntry(
            id=row.id,
            identifier=row.identifier,
            name=row.name,
            type=row.type,
            parent_id=row.parent_id,
            location=row.location,
            provider=row.provider,
            specifications=row.specifications or {},
            status=row.status,
            review_status=row.review_status,
            confidence_score=row.confidence_score,
            version=row.version or 1,
            notes=row.notes,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )


def get_asset_registry_service(
    session: Optional[Session] = None,
) -> AssetRegistryService:
    return AssetRegistryService(session=session)
