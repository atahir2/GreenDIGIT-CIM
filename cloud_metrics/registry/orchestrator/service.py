"""Registry Orchestrator service — Milestone 7.

Coordinates Metric / Mapping / Unit / Source / Asset registries during
ingestion. Does not replace ``process_metric_sample``; callers opt in.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Mapping, Optional

from sqlalchemy.orm import Session

from cloud_metrics.registry.mapping.service import resolve_raw_metric
from cloud_metrics.registry.migration.gd_to_cim import GD_TO_CIM
from cloud_metrics.registry.orchestrator.types import OrchestratorResult, RawMetricContext

logger = logging.getLogger(__name__)

# Reverse of trusted alignments for storage-key adaptation (gd.* for legacy sinks).
_CIM_TO_GD: Dict[str, str] = {v: k for k, v in GD_TO_CIM.items()}


def cim_namespace_to_storage_key(cim_namespace: Optional[str]) -> Optional[str]:
    """Map a ``cim:*`` namespace to a legacy ``gd.*`` storage key when possible."""
    if not cim_namespace:
        return None
    ns = cim_namespace.strip()
    if ns in _CIM_TO_GD:
        return _CIM_TO_GD[ns]
    if ns.startswith("cim:"):
        return "gd." + ns[4:]
    if ns.startswith("gd."):
        return ns
    return f"gd.extension.{ns.replace(':', '_').replace('.', '_')}"


def _merge_context(ctx: RawMetricContext) -> Dict[str, Any]:
    """Build a single metadata dict for source/asset extractors."""
    out: Dict[str, Any] = {}
    if ctx.original_raw_metadata:
        out.update(ctx.original_raw_metadata)
    if ctx.source_metadata:
        out.update(ctx.source_metadata)
    if ctx.asset_labels:
        out.update(ctx.asset_labels)
    if ctx.tags:
        # Flatten tags under tags= and also top-level for extractors
        out.setdefault("tags", ctx.tags)
        for k, v in ctx.tags.items():
            out.setdefault(k, v)
    if ctx.labels:
        out.setdefault("labels", ctx.labels)
        for k, v in ctx.labels.items():
            out.setdefault(k, v)
    if ctx.source:
        out.setdefault("source", ctx.source)
        out.setdefault("source_name", ctx.source)
    if ctx.source_type:
        out.setdefault("source_type", ctx.source_type)
    return out


class RegistryOrchestratorService:
    """Central coordinator for registry-driven metric resolution during ingestion."""

    def __init__(self, session: Optional[Session] = None) -> None:
        self._session = session

    def process(
        self,
        ctx: RawMetricContext,
        *,
        use_fallback: bool = True,
        create_candidate_on_fallback: bool = True,
        create_source_candidate: bool = True,
        create_asset_candidate: bool = True,
        validate_unit: Optional[bool] = None,
        resolve_source: Optional[bool] = None,
        resolve_asset: Optional[bool] = None,
    ) -> OrchestratorResult:
        """Run registry-first mapping + soft unit/source/asset enrichment.

        Never raises for unresolved metrics. Always returns an
        ``OrchestratorResult`` with status / warnings / errors populated.
        """
        raw = (ctx.raw_metric_name or "").strip()
        logger.info("registry orchestrator invoked: raw=%s", raw)

        meta = _merge_context(ctx)
        has_context = bool(meta)

        # Default: resolve source/asset when any context metadata is present
        do_source = resolve_source if resolve_source is not None else has_context
        do_asset = resolve_asset if resolve_asset is not None else has_context

        try:
            lookup = resolve_raw_metric(
                raw,
                session=self._session,
                use_fallback=use_fallback,
                create_candidate_on_fallback=create_candidate_on_fallback,
                observed_unit=ctx.unit,
                validate_unit=validate_unit,
                context=meta if has_context else None,
                resolve_source=do_source,
                resolve_asset=do_asset,
                create_source_candidate=create_source_candidate,
                create_asset_candidate=create_asset_candidate,
            )
        except Exception as exc:
            logger.exception("registry orchestrator error: raw=%s", raw)
            return OrchestratorResult(
                raw_metric_name=raw,
                mapping_status="unresolved",
                resolved=False,
                resolution_path="unresolved",
                errors=[f"orchestrator exception: {exc}"],
                original_raw_metadata=dict(meta),
                observed_unit=ctx.unit,
                message=str(exc),
            )

        return self._to_result(ctx, meta, lookup)

    def _to_result(
        self,
        ctx: RawMetricContext,
        meta: Mapping[str, Any],
        lookup,
    ) -> OrchestratorResult:
        warnings: list[str] = []
        errors: list[str] = []
        candidate_flags: Dict[str, bool] = {
            "mapping_candidate": False,
            "metric_unresolved": False,
            "unit_unknown": False,
            "unit_incompatible": False,
            "source_missing": False,
            "source_candidate": False,
            "asset_missing": False,
            "asset_candidate": False,
        }

        fallback_used = lookup.resolution_path == "legacy_fallback"
        if lookup.resolution_path == "registry":
            logger.info(
                "registry mapping hit: raw=%s → %s",
                lookup.raw_key,
                lookup.cim_namespace,
            )
        elif fallback_used:
            logger.info(
                "legacy fallback used: raw=%s → legacy=%s cim=%s",
                lookup.raw_key,
                lookup.legacy_unified_key,
                lookup.cim_namespace,
            )
        else:
            logger.info("unresolved/candidate metric: raw=%s", lookup.raw_key)
            candidate_flags["metric_unresolved"] = True

        mapping_status = lookup.status or "unresolved"
        if mapping_status == "candidate":
            candidate_flags["mapping_candidate"] = True
        if not lookup.resolved:
            candidate_flags["metric_unresolved"] = True
            # Do not silently approve
            if mapping_status in {"approved", "active"}:
                mapping_status = "unresolved"

        metric_definition_id = None
        confidence = None
        relation_type = None
        if lookup.mapping is not None:
            metric_definition_id = lookup.mapping.cim_metric_id
            confidence = lookup.mapping.confidence
            relation_type = lookup.mapping.relation_type

        # Unit validation
        unit_status = None
        observed_unit = ctx.unit
        canonical_unit = lookup.canonical_unit
        expected_qk = lookup.expected_quantity_kind
        if lookup.unit_validation is not None:
            uv = lookup.unit_validation
            unit_status = uv.validation_status
            observed_unit = uv.observed_unit if uv.observed_unit is not None else observed_unit
            canonical_unit = uv.canonical_unit or canonical_unit
            expected_qk = uv.expected_quantity_kind or expected_qk
            logger.info(
                "unit validation result: raw=%s status=%s severity=%s",
                lookup.raw_key,
                uv.validation_status,
                uv.severity,
            )
            if uv.validation_status == "unknown":
                candidate_flags["unit_unknown"] = True
                warnings.append(uv.message or "unknown unit")
            elif uv.validation_status == "incompatible":
                candidate_flags["unit_incompatible"] = True
                warnings.append(uv.message or "incompatible unit")
            elif uv.validation_status == "missing" and ctx.unit is None:
                warnings.append(uv.message or "missing observed unit")
            elif uv.severity == "warning" and uv.message:
                warnings.append(uv.message)
            elif uv.severity == "error" and uv.message:
                errors.append(uv.message)

        # Source resolution
        source_status = None
        source_id = None
        if lookup.source_resolution is not None:
            sr = lookup.source_resolution
            source_status = sr.resolution_status
            source_id = sr.source_id
            logger.info(
                "source resolution result: raw=%s status=%s id=%s",
                lookup.raw_key,
                sr.resolution_status,
                sr.source_id,
            )
            if sr.resolution_status == "missing":
                candidate_flags["source_missing"] = True
                warnings.extend(sr.warnings or ["missing source"])
            elif sr.resolution_status == "candidate_created":
                candidate_flags["source_candidate"] = True
            elif sr.warnings:
                warnings.extend(sr.warnings)

        # Asset resolution
        asset_status = None
        asset_id = None
        if lookup.asset_resolution is not None:
            ar = lookup.asset_resolution
            asset_status = ar.resolution_status
            asset_id = ar.asset_id
            logger.info(
                "asset resolution result: raw=%s status=%s id=%s",
                lookup.raw_key,
                ar.resolution_status,
                ar.asset_id,
            )
            if ar.resolution_status == "missing":
                candidate_flags["asset_missing"] = True
                warnings.extend(ar.warnings or ["missing asset"])
            elif ar.resolution_status == "candidate_created":
                candidate_flags["asset_candidate"] = True
            elif ar.warnings:
                warnings.extend(ar.warnings)

        if lookup.message and not lookup.resolved:
            warnings.append(lookup.message)

        storage_key = lookup.legacy_unified_key or cim_namespace_to_storage_key(
            lookup.cim_namespace
        )

        if any(candidate_flags.values()) or warnings:
            logger.info(
                "orchestrator warnings/errors: raw=%s flags=%s warnings=%s errors=%s",
                lookup.raw_key,
                {k: v for k, v in candidate_flags.items() if v},
                warnings,
                errors,
            )

        return OrchestratorResult(
            raw_metric_name=lookup.raw_key or ctx.raw_metric_name,
            cim_namespace=lookup.cim_namespace,
            metric_definition_id=metric_definition_id,
            mapping_status=mapping_status,
            mapping_confidence=confidence,
            unit_validation_status=unit_status,
            observed_unit=observed_unit,
            canonical_unit=canonical_unit,
            expected_quantity_kind=expected_qk,
            source_resolution_status=source_status,
            source_id=source_id,
            asset_resolution_status=asset_status,
            asset_id=asset_id,
            candidate_flags=candidate_flags,
            warnings=warnings,
            errors=errors,
            fallback_used=fallback_used,
            original_raw_metadata=dict(meta),
            resolved=bool(lookup.resolved),
            resolution_path=lookup.resolution_path,
            legacy_unified_key=lookup.legacy_unified_key,
            storage_unified_key=storage_key,
            relation_type=relation_type,
            message=lookup.message,
        )


def get_registry_orchestrator(
    session: Optional[Session] = None,
) -> RegistryOrchestratorService:
    return RegistryOrchestratorService(session=session)


# Alias matching suggested naming in the milestone brief
CimRegistryOrchestrator = RegistryOrchestratorService
RegistryOrchestrator = RegistryOrchestratorService
