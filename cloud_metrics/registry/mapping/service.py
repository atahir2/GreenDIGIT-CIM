"""Mapping Registry service — registry-first lookup with legacy fallback.

Milestone 4 wires persistence against ``cim_metric_mappings`` when a SQLAlchemy
session is provided. Without a session the service remains a no-op skeleton so
Milestone 1 smoke tests and callers that do not opt in keep working.

Ingestion is **not** forced onto this path yet; use
``resolve_raw_metric()`` or ``MappingRegistryService.resolve_with_fallback()``
explicitly.
"""

from __future__ import annotations

import logging
from typing import Any, List, Mapping, Optional, Dict

from sqlalchemy import func
from sqlalchemy.orm import Session

from cloud_metrics.registry.base import RegistryName, SKELETON_ONLY
from cloud_metrics.registry.mapping.types import MappingEntry, MappingLookupResult
from cloud_metrics.registry.migration.gd_to_cim import resolve_cim_namespace

logger = logging.getLogger(__name__)

_ACTIVE_MAPPING_STATUSES = frozenset({"approved", "active"})


class MappingRegistryService:
    """Mapping Registry with optional DB session and legacy fallback."""

    registry_name = RegistryName.MAPPING
    # Not wired into ingestion yet — callers must opt in.
    skeleton_only = SKELETON_ONLY

    def __init__(self, session: Optional[Session] = None) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # Skeleton-compatible surface (empty without session)
    # ------------------------------------------------------------------

    def list_entries(self) -> List[MappingEntry]:
        if self._session is None:
            return []
        from cloud_metrics.models.cim_registry import CimMetricMapping

        rows = (
            self._session.query(CimMetricMapping)
            .filter(CimMetricMapping.status.in_(tuple(_ACTIVE_MAPPING_STATUSES)))
            .all()
        )
        return [self._to_entry(row) for row in rows]

    def resolve(self, source_key: str) -> Optional[MappingEntry]:
        """Registry-only resolve (approved/active mappings). No legacy fallback."""
        result = self.resolve_with_fallback(
            source_key,
            use_fallback=False,
            create_candidate_on_fallback=False,
        )
        if result.resolved and result.mapping is not None:
            return result.mapping
        return None

    def propose(self, entry: MappingEntry) -> MappingEntry:
        """Echo / optional persist a proposed mapping (opt-in session)."""
        if self._session is None:
            return entry
        from cloud_metrics.models.cim_registry import (
            CimMetricDefinition,
            CimMetricMapping,
        )

        metric = None
        if entry.cim_metric_id:
            metric = (
                self._session.query(CimMetricDefinition)
                .filter_by(id=entry.cim_metric_id)
                .first()
            )
        elif entry.cim_namespace:
            metric = (
                self._session.query(CimMetricDefinition)
                .filter_by(namespace=entry.cim_namespace)
                .first()
            )
        if metric is None:
            return entry

        existing = (
            self._session.query(CimMetricMapping)
            .filter(
                func.lower(CimMetricMapping.source_key) == entry.source_key.lower(),
                CimMetricMapping.source_id.is_(None)
                if entry.source_id is None
                else CimMetricMapping.source_id == entry.source_id,
            )
            .first()
        )
        if existing:
            return self._to_entry(existing)

        row = CimMetricMapping(
            source_key=entry.source_key,
            source_id=entry.source_id,
            metric_id=metric.id,
            relation_type=entry.relation_type or "underReview",
            rationale=entry.rationale,
            origin=entry.origin or "manual",
            status=entry.status or "candidate",
            review_status=entry.review_status or "under_review",
            confidence_score=entry.confidence,
            version=entry.version or 1,
            created_by="mapping_registry_service",
        )
        self._session.add(row)
        self._session.flush()
        logger.info(
            "candidate mapping created: raw=%s → %s",
            entry.source_key,
            metric.namespace,
        )
        return self._to_entry(row)

    # ------------------------------------------------------------------
    # Milestone 4: registry-first + legacy fallback
    # ------------------------------------------------------------------

    def resolve_with_fallback(
        self,
        raw_key: str,
        *,
        source_id: Optional[int] = None,
        use_fallback: bool = True,
        create_candidate_on_fallback: bool = False,
        observed_unit: Optional[str] = None,
        validate_unit: Optional[bool] = None,
        context: Optional[Mapping[str, Any]] = None,
        resolve_source: Optional[bool] = None,
        resolve_asset: Optional[bool] = None,
        create_source_candidate: bool = True,
        create_asset_candidate: bool = True,
    ) -> MappingLookupResult:
        """Resolve ``raw_key`` via registry, then optional legacy fallback.

        Milestone 5: soft unit validation when ``observed_unit`` is set.
        Milestone 6: soft source/asset resolution when ``context`` is set
        (or when ``resolve_source`` / ``resolve_asset`` is True).
        Enrichment never flips ``resolved`` to False.
        """
        key = (raw_key or "").strip()
        if not key:
            return MappingLookupResult(
                raw_key=raw_key or "",
                resolved=False,
                resolution_path="unresolved",
                status="unresolved",
                message="empty raw key",
            )

        result: Optional[MappingLookupResult] = None

        if self._session is not None:
            hit = self._registry_lookup(key, source_id=source_id)
            if hit is not None:
                logger.info(
                    "registry mapping hit: raw=%s → %s status=%s",
                    key,
                    hit.cim_namespace,
                    hit.status,
                )
                result = MappingLookupResult(
                    raw_key=key,
                    resolved=True,
                    resolution_path="registry",
                    cim_namespace=hit.cim_namespace,
                    legacy_unified_key=hit.legacy_unified_key,
                    mapping=hit,
                    status="approved"
                    if hit.status in _ACTIVE_MAPPING_STATUSES
                    else hit.status,
                    message="registry hit",
                    expected_quantity_kind=hit.expected_quantity_kind,
                    canonical_unit=hit.canonical_unit,
                )

        if result is None and not use_fallback:
            logger.info("unresolved metric (registry-only): raw=%s", key)
            return MappingLookupResult(
                raw_key=key,
                resolved=False,
                resolution_path="unresolved",
                status="unresolved",
                message="no registry mapping",
            )

        if result is None:
            legacy = self._legacy_fallback(key)
            if legacy is None:
                logger.info("unresolved metric: raw=%s", key)
                unresolved = MappingLookupResult(
                    raw_key=key,
                    resolved=False,
                    resolution_path="unresolved",
                    status="unresolved",
                    message="no registry or legacy mapping",
                )
                self._attach_context_resolution(
                    unresolved,
                    context=context,
                    resolve_source=resolve_source,
                    resolve_asset=resolve_asset,
                    create_source_candidate=create_source_candidate,
                    create_asset_candidate=create_asset_candidate,
                )
                return unresolved

            logger.info(
                "legacy fallback hit: raw=%s → legacy=%s cim=%s",
                key,
                legacy.legacy_unified_key,
                legacy.cim_namespace,
            )

            candidate_created = False
            if create_candidate_on_fallback and self._session is not None:
                candidate_created = self._backfill_candidate(key, legacy)

            # Enrich expectations from metric registry when possible
            self._enrich_metric_expectations(legacy)

            result = MappingLookupResult(
                raw_key=key,
                resolved=True,
                resolution_path="legacy_fallback",
                cim_namespace=legacy.cim_namespace,
                legacy_unified_key=legacy.legacy_unified_key,
                mapping=legacy,
                status="candidate",
                message="legacy fallback; registry backfill recommended"
                if not candidate_created
                else "legacy fallback; candidate mapping created",
                candidate_created=candidate_created,
                expected_quantity_kind=legacy.expected_quantity_kind,
                canonical_unit=legacy.canonical_unit,
            )

        assert result is not None
        self._attach_unit_validation(
            result,
            observed_unit=observed_unit,
            validate_unit=validate_unit,
        )
        self._attach_context_resolution(
            result,
            context=context,
            resolve_source=resolve_source,
            resolve_asset=resolve_asset,
            create_source_candidate=create_source_candidate,
            create_asset_candidate=create_asset_candidate,
        )
        return result

    def _should_resolve_context(
        self,
        *,
        context: Optional[Mapping[str, Any]],
        flag: Optional[bool],
    ) -> bool:
        if flag is False:
            return False
        if flag is True:
            return True
        return context is not None

    def _attach_context_resolution(
        self,
        result: MappingLookupResult,
        *,
        context: Optional[Mapping[str, Any]],
        resolve_source: Optional[bool],
        resolve_asset: Optional[bool],
        create_source_candidate: bool,
        create_asset_candidate: bool,
    ) -> None:
        """Soft source/asset enrichment — never changes ``resolved``."""
        do_source = self._should_resolve_context(
            context=context, flag=resolve_source
        )
        do_asset = self._should_resolve_context(context=context, flag=resolve_asset)
        if not do_source and not do_asset:
            return
        if self._session is None:
            return

        ctx = dict(context or {})

        if do_source:
            from cloud_metrics.registry.source.service import SourceRegistryService

            src_svc = SourceRegistryService(session=self._session)
            if ctx:
                result.source_resolution = src_svc.resolve_from_metadata(
                    ctx, create_candidate=create_source_candidate
                )
            else:
                result.source_resolution = src_svc.resolve_or_create(
                    name=None, create_candidate=False
                )
            if (
                result.source_resolution
                and result.source_resolution.source_id
                and result.mapping is not None
                and result.mapping.source_id is None
            ):
                result.mapping.source_id = result.source_resolution.source_id

        if do_asset:
            from cloud_metrics.registry.asset.service import AssetRegistryService

            asset_svc = AssetRegistryService(session=self._session)
            if ctx:
                result.asset_resolution = asset_svc.resolve_from_metadata(
                    ctx, create_candidate=create_asset_candidate
                )
            else:
                from cloud_metrics.registry.asset.types import AssetResolutionResult

                result.asset_resolution = AssetResolutionResult(
                    resolution_status="missing",
                    message="No context metadata for asset resolution",
                    warnings=["empty context"],
                )

    def _should_validate_unit(
        self,
        *,
        observed_unit: Optional[str],
        validate_unit: Optional[bool],
    ) -> bool:
        if validate_unit is False:
            return False
        if validate_unit is True:
            return True
        # Default: only validate when a unit was supplied (backward compatible)
        return observed_unit is not None

    def _enrich_metric_expectations(self, entry: MappingEntry) -> None:
        if self._session is None or not entry.cim_namespace:
            return
        if entry.expected_quantity_kind and entry.canonical_unit:
            return
        from cloud_metrics.models.cim_registry import CimMetricDefinition

        metric = (
            self._session.query(CimMetricDefinition)
            .filter_by(namespace=entry.cim_namespace)
            .first()
        )
        if metric is None:
            return
        if metric.quantity_kind is not None:
            entry.expected_quantity_kind = metric.quantity_kind.name
        if metric.canonical_unit is not None:
            entry.canonical_unit = metric.canonical_unit.symbol

    def _attach_unit_validation(
        self,
        result: MappingLookupResult,
        *,
        observed_unit: Optional[str],
        validate_unit: Optional[bool],
    ) -> None:
        if not result.resolved or not result.cim_namespace:
            return
        if not self._should_validate_unit(
            observed_unit=observed_unit, validate_unit=validate_unit
        ):
            return

        from cloud_metrics.registry.unit.service import UnitRegistryService

        unit_svc = UnitRegistryService(session=self._session)
        uv = unit_svc.validate_for_metric(
            result.cim_namespace,
            observed_unit=observed_unit,
        )
        result.unit_validation = uv
        result.expected_quantity_kind = (
            result.expected_quantity_kind or uv.expected_quantity_kind
        )
        result.canonical_unit = result.canonical_unit or uv.canonical_unit
        if result.mapping is not None:
            result.mapping.expected_quantity_kind = (
                result.mapping.expected_quantity_kind or uv.expected_quantity_kind
            )
            result.mapping.canonical_unit = (
                result.mapping.canonical_unit or uv.canonical_unit
            )


    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _registry_lookup(
        self, raw_key: str, *, source_id: Optional[int] = None
    ) -> Optional[MappingEntry]:
        assert self._session is not None
        from cloud_metrics.models.cim_registry import CimMetricMapping

        q = self._session.query(CimMetricMapping).filter(
            func.lower(CimMetricMapping.source_key) == raw_key.lower(),
            CimMetricMapping.status.in_(tuple(_ACTIVE_MAPPING_STATUSES)),
        )
        if source_id is not None:
            q = q.filter(CimMetricMapping.source_id == source_id)
        row = q.first()
        if row is None and source_id is not None:
            # Fall back to source-agnostic approved mapping
            row = (
                self._session.query(CimMetricMapping)
                .filter(
                    func.lower(CimMetricMapping.source_key) == raw_key.lower(),
                    CimMetricMapping.status.in_(tuple(_ACTIVE_MAPPING_STATUSES)),
                    CimMetricMapping.source_id.is_(None),
                )
                .first()
            )
        return self._to_entry(row) if row else None

    def _legacy_fallback(self, raw_key: str) -> Optional[MappingEntry]:
        # 1) JSON / namespace_mapper
        try:
            from cloud_metrics.mapping.namespace_mapper import map_raw_to_unified

            unified = map_raw_to_unified(raw_key, 0.0)
            if unified is not None:
                cim_ns, _ = resolve_cim_namespace(unified.name)
                return MappingEntry(
                    source_key=raw_key,
                    cim_namespace=cim_ns,
                    legacy_unified_key=unified.name,
                    relation_type="exactMatch",
                    confidence=1.0,
                    status="candidate",
                    review_status="pending",
                    origin="legacy_fallback",
                    rationale="Resolved via metric_mapping.json / namespace_mapper",
                )
        except Exception as exc:
            logger.debug("namespace_mapper fallback failed: %s", exc)

        # 2) Legacy CimMapping table (Antigravity)
        try:
            from cloud_metrics.services.mapping_registry_service import resolve_mapping

            cm = resolve_mapping(raw_key)
            if cm is not None and getattr(cm, "cim_metric", None) is not None:
                uk = cm.cim_metric.unified_key
                cim_ns, _ = resolve_cim_namespace(uk)
                return MappingEntry(
                    source_key=raw_key,
                    cim_namespace=cim_ns,
                    legacy_unified_key=uk,
                    relation_type=getattr(cm, "relation_type", "closeMatch") or "closeMatch",
                    confidence=float(getattr(cm, "confidence", 0.9) or 0.9),
                    status="candidate",
                    review_status="pending",
                    origin="legacy_fallback",
                    rationale="Resolved via legacy CimMapping registry",
                )
        except Exception as exc:
            logger.debug("CimMapping fallback failed: %s", exc)

        # 3) Alias classifier
        try:
            from cloud_metrics.classifiers.alias_classifier import guess_from_alias
            from cloud_metrics.registry.migration.gd_to_cim import triple_to_gd

            hit = guess_from_alias(raw_key)
            if hit is not None:
                gd = triple_to_gd(hit.category, hit.subcategory, hit.short_key)
                cim_ns, _ = resolve_cim_namespace(gd)
                return MappingEntry(
                    source_key=raw_key,
                    cim_namespace=cim_ns,
                    legacy_unified_key=gd,
                    relation_type="closeMatch",
                    confidence=float(hit.score) / 100.0,
                    status="candidate",
                    review_status="pending",
                    origin="legacy_fallback",
                    rationale=f"Alias match: {hit.matched_alias}",
                )
        except Exception as exc:
            logger.debug("alias fallback failed: %s", exc)

        return None

    def _backfill_candidate(self, raw_key: str, entry: MappingEntry) -> bool:
        """Optionally create a candidate registry mapping after legacy hit."""
        assert self._session is not None
        if not entry.cim_namespace:
            return False
        from cloud_metrics.models.cim_registry import CimMetricDefinition

        metric = (
            self._session.query(CimMetricDefinition)
            .filter_by(namespace=entry.cim_namespace)
            .first()
        )
        if metric is None:
            metric = CimMetricDefinition(
                namespace=entry.cim_namespace,
                label=entry.cim_namespace.rsplit(".", 1)[-1],
                description="Candidate from legacy fallback backfill",
                status="candidate",
                review_status="under_review",
                confidence_score=entry.confidence,
                version=1,
                created_by="mapping_registry_fallback",
                notes=f"Backfill from legacy key {entry.legacy_unified_key}",
                tags=["fallback_backfill", "candidate"],
            )
            self._session.add(metric)
            self._session.flush()
            logger.info(
                "candidate metric definition created: namespace=%s",
                entry.cim_namespace,
            )

        proposed = MappingEntry(
            source_key=raw_key,
            cim_namespace=entry.cim_namespace,
            cim_metric_id=metric.id,
            relation_type="underReview",
            confidence=entry.confidence,
            rationale=entry.rationale or "Backfilled after legacy fallback",
            status="candidate",
            review_status="under_review",
            origin="legacy_fallback",
            legacy_unified_key=entry.legacy_unified_key,
        )
        before = self.propose(proposed)
        created = before.id is not None
        if created:
            logger.info(
                "candidate mapping created: raw=%s → %s",
                raw_key,
                entry.cim_namespace,
            )
        return created

    def _to_entry(self, row) -> MappingEntry:
        metric = getattr(row, "metric", None)
        namespace = metric.namespace if metric is not None else None
        qk = None
        canon = None
        if metric is not None:
            if metric.quantity_kind is not None:
                qk = metric.quantity_kind.name
            if metric.canonical_unit is not None:
                canon = metric.canonical_unit.symbol
        return MappingEntry(
            id=row.id,
            source_key=row.source_key,
            cim_namespace=namespace,
            source_id=row.source_id,
            cim_metric_id=row.metric_id,
            standard_id=row.standard_id,
            relation_type=row.relation_type,
            confidence=float(row.confidence_score or 1.0),
            rationale=row.rationale,
            approved_by=row.approved_by,
            approved_at=row.approved_at,
            status=row.status,
            review_status=row.review_status,
            version=row.version or 1,
            origin=row.origin or "manual",
            created_at=row.created_at,
            updated_at=row.updated_at,
            expected_quantity_kind=qk,
            canonical_unit=canon,
            extra={"notes": row.notes} if row.notes else {},
        )


def get_mapping_registry_service(
    session: Optional[Session] = None,
) -> MappingRegistryService:
    return MappingRegistryService(session=session)


def resolve_raw_metric(
    raw_key: str,
    session: Optional[Session] = None,
    *,
    use_fallback: bool = True,
    create_candidate_on_fallback: bool = False,
    observed_unit: Optional[str] = None,
    validate_unit: Optional[bool] = None,
    source_id: Optional[int] = None,
    context: Optional[Mapping[str, Any]] = None,
    resolve_source: Optional[bool] = None,
    resolve_asset: Optional[bool] = None,
    create_source_candidate: bool = True,
    create_asset_candidate: bool = True,
) -> MappingLookupResult:
    """Convenience entry point for registry-first mapping lookup.

    Safe for callers: never raises on unresolved metrics; returns status instead.
    Does not replace legacy ``resolve_mapping`` / ``map_raw_to_unified``.

    Milestone 5: pass ``observed_unit`` to attach soft unit validation metadata.
    Milestone 6: pass ``context`` (labels/metadata) to attach soft source/asset
    resolution metadata.
    """
    svc = get_mapping_registry_service(session=session)
    return svc.resolve_with_fallback(
        raw_key,
        source_id=source_id,
        use_fallback=use_fallback,
        create_candidate_on_fallback=create_candidate_on_fallback,
        observed_unit=observed_unit,
        validate_unit=validate_unit,
        context=context,
        resolve_source=resolve_source,
        resolve_asset=resolve_asset,
        create_source_candidate=create_source_candidate,
        create_asset_candidate=create_asset_candidate,
    )
