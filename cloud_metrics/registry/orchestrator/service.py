"""Registry Orchestrator service — Milestone 7–8.

Coordinates Metric / Mapping / Unit / Source / Asset / Lifecycle / Standards
registries during ingestion. Does not replace ``process_metric_sample``;
callers opt in.
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
_APPROVED_STATUSES = frozenset({"approved", "active"})


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
        attach_lifecycle: bool = True,
        attach_standards: bool = True,
        attach_governance: bool = True,
        record_provenance: bool = True,
        create_extension_on_unresolved: bool = True,
    ) -> OrchestratorResult:
        """Run registry-first mapping + soft enrichment + governance.

        Milestone 9: optionally applies rules, evidence, provenance, extension.
        Never raises for unresolved metrics; does not hard-block ingestion.
        """
        raw = (ctx.raw_metric_name or "").strip()
        logger.info("registry orchestrator invoked: raw=%s", raw)

        meta = _merge_context(ctx)
        has_context = bool(meta)

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
                no_direct_standard_match=True,
                review_required=True,
            )

        result = self._to_result(ctx, meta, lookup)
        if attach_lifecycle or attach_standards:
            self._attach_lifecycle_and_standards(
                result,
                attach_lifecycle=attach_lifecycle,
                attach_standards=attach_standards,
            )
        if attach_governance:
            self._attach_governance(
                result,
                ctx,
                meta,
                record_provenance=record_provenance,
                create_extension_on_unresolved=create_extension_on_unresolved,
            )
        return result

    def _attach_governance(
        self,
        result: OrchestratorResult,
        ctx: RawMetricContext,
        meta: Mapping[str, Any],
        *,
        record_provenance: bool,
        create_extension_on_unresolved: bool,
    ) -> None:
        """Soft Rule / Evidence / Extension / Provenance enrichment."""
        gov_warnings: list[str] = []
        gov_errors: list[str] = []
        review_required = bool(
            result.candidate_flags.get("metric_unresolved")
            or result.candidate_flags.get("mapping_candidate")
            or result.fallback_used
            or not result.resolved
        )

        # --- Extension candidates for unresolved / unknown ---
        if (
            create_extension_on_unresolved
            and self._session is not None
            and (
                not result.resolved
                or result.candidate_flags.get("metric_unresolved")
            )
        ):
            try:
                from cloud_metrics.registry.extension import ExtensionRegistryService

                ext_svc = ExtensionRegistryService(session=self._session)
                ext = ext_svc.propose_from_raw(
                    result.raw_metric_name,
                    source_context=dict(meta) if meta else None,
                    suggested_unit=result.observed_unit or ctx.unit,
                    confidence_score=result.mapping_confidence,
                )
                result.extension_candidate_id = ext.id
                review_required = True
                if not ext.is_approved:
                    result.candidate_flags["extension_candidate"] = True
                logger.info(
                    "extension candidate: raw=%s id=%s status=%s",
                    result.raw_metric_name,
                    ext.id,
                    ext.review_status,
                )
            except Exception as exc:
                logger.warning("extension candidate failed: %s", exc)
                gov_warnings.append(f"extension candidate failed: {exc}")

        # --- Metric definition hints for rules / evidence ---
        metric_type = None
        domain = None
        category = None
        quantity_kind = result.expected_quantity_kind
        if self._session is not None and (
            result.metric_definition_id or result.cim_namespace
        ):
            try:
                from cloud_metrics.models.cim_registry import CimMetricDefinition

                metric = None
                if result.metric_definition_id:
                    metric = self._session.get(
                        CimMetricDefinition, result.metric_definition_id
                    )
                if metric is None and result.cim_namespace:
                    metric = (
                        self._session.query(CimMetricDefinition)
                        .filter_by(namespace=result.cim_namespace)
                        .first()
                    )
                if metric is not None:
                    metric_type = metric.metric_type
                    domain = metric.domain
                    category = metric.category
                    if metric.quantity_kind is not None:
                        quantity_kind = metric.quantity_kind.name
                    if result.metric_definition_id is None:
                        result.metric_definition_id = metric.id
            except Exception as exc:
                logger.debug("metric def lookup for governance failed: %s", exc)

        # --- Rules ---
        try:
            from cloud_metrics.registry.rule import RuleRegistryService

            rule_svc = RuleRegistryService(session=self._session)
            payload: Dict[str, Any] = {
                "namespace": result.cim_namespace or result.storage_unified_key,
                "metric_type": metric_type,
                "domain": domain,
                "category": category,
                "quantity_kind": quantity_kind,
                "expected_quantity_kind": result.expected_quantity_kind,
                "observed_unit": result.observed_unit or ctx.unit,
                "canonical_unit": result.canonical_unit,
                "unit": result.observed_unit or ctx.unit,
                "unit_validation_status": result.unit_validation_status,
                "timestamp": ctx.timestamp,
                "source": ctx.source or meta.get("source") or meta.get("source_name"),
                "source_id": result.source_id,
                "value": ctx.value,
                "aggregation_period": ctx.aggregation_period
                or meta.get("aggregation_period"),
                "boundary": ctx.boundary or meta.get("boundary"),
                "formula_or_derivation_method": ctx.formula_or_derivation_method
                or meta.get("formula_or_derivation_method")
                or meta.get("formula"),
                "workflow_id": ctx.workflow_id
                or meta.get("workflow_id")
                or meta.get("workflow"),
                "run_id": ctx.run_id
                or meta.get("run_id")
                or meta.get("workflow_run_id"),
                "lifecycle_stages": list(result.lifecycle_stages),
                "is_extension": bool(result.extension_candidate_id)
                or (result.cim_namespace or "").startswith("cim:extension."),
                "justification": meta.get("justification"),
                "review_status": result.mapping_status,
            }
            eval_res = rule_svc.evaluate(payload)
            result.validation_results = list(eval_res.results)
            result.rule_results = list(eval_res.results)
            gov_warnings.extend(eval_res.warnings)
            gov_errors.extend(eval_res.errors)
            if eval_res.has_critical or any(
                (not r.passed and r.severity in {"error", "critical"})
                for r in eval_res.results
            ):
                review_required = True
        except Exception as exc:
            logger.warning("rule evaluation failed: %s", exc)
            gov_warnings.append(f"rule evaluation failed: {exc}")

        # --- Evidence (reportable / seeded metrics only) ---
        if self._session is not None and result.cim_namespace and result.resolved:
            try:
                from cloud_metrics.registry.evidence import EvidenceRegistryService

                ev_svc = EvidenceRegistryService(session=self._session)
                ev_res = ev_svc.get_requirements_for_metric(
                    result.cim_namespace,
                    metric_id=result.metric_definition_id,
                )
                result.evidence_requirements = list(ev_res.requirements)
                result.evidence_readiness_status = ev_res.readiness_status
            except Exception as exc:
                logger.warning("evidence lookup failed: %s", exc)
                gov_warnings.append(f"evidence lookup failed: {exc}")
                result.evidence_readiness_status = "unknown"
        elif not result.resolved:
            result.evidence_readiness_status = "not_applicable"

        # --- Provenance ---
        if record_provenance and self._session is not None:
            try:
                from cloud_metrics.registry.provenance import ProvenanceRegistryService

                prov = ProvenanceRegistryService(session=self._session)
                entity_id = result.metric_definition_id or result.extension_candidate_id
                # Primary orchestration record
                main = prov.record_activity(
                    entity_type="orchestrator_result",
                    entity_id=entity_id,
                    activity="orchestration",
                    agent="registry_orchestrator",
                    method="RegistryOrchestratorService.process",
                    confidence=result.mapping_confidence,
                    inputs={
                        "raw_metric_name": result.raw_metric_name,
                        "unit": ctx.unit,
                        "source": ctx.source,
                    },
                    outputs={
                        "cim_namespace": result.cim_namespace,
                        "resolved": result.resolved,
                        "resolution_path": result.resolution_path,
                        "mapping_status": result.mapping_status,
                        "fallback_used": result.fallback_used,
                        "extension_candidate_id": result.extension_candidate_id,
                    },
                    notes="registry orchestrator decision",
                )
                result.provenance_record_id = main.id
                result.provenance_log_reference = (
                    f"cim_provenance_records:{main.id}" if main.id else None
                )

                # Sub-events (best effort)
                events = [
                    (
                        "registry_mapping_lookup",
                        {
                            "path": result.resolution_path,
                            "namespace": result.cim_namespace,
                        },
                    ),
                ]
                if result.fallback_used:
                    events.append(
                        (
                            "legacy_fallback",
                            {"legacy_unified_key": result.legacy_unified_key},
                        )
                    )
                if result.unit_validation_status:
                    events.append(
                        (
                            "unit_validation",
                            {"status": result.unit_validation_status},
                        )
                    )
                if result.source_resolution_status:
                    events.append(
                        (
                            "source_resolution",
                            {
                                "status": result.source_resolution_status,
                                "source_id": result.source_id,
                            },
                        )
                    )
                if result.asset_resolution_status:
                    events.append(
                        (
                            "asset_resolution",
                            {
                                "status": result.asset_resolution_status,
                                "asset_id": result.asset_id,
                            },
                        )
                    )
                if result.lifecycle_stages:
                    events.append(
                        ("lifecycle_mapping_retrieval", {"stages": result.lifecycle_stages})
                    )
                if result.standards_mappings or result.no_direct_standard_match:
                    events.append(
                        (
                            "standards_mapping_retrieval",
                            {
                                "relations": result.standards_relation_types,
                                "no_direct": result.no_direct_standard_match,
                            },
                        )
                    )
                if result.validation_results:
                    events.append(
                        (
                            "validation_rule_application",
                            {
                                "count": len(result.validation_results),
                                "failed": [
                                    v.rule_name
                                    for v in result.validation_results
                                    if not v.passed
                                ],
                            },
                        )
                    )
                if result.evidence_requirements:
                    events.append(
                        (
                            "evidence_requirement_retrieval",
                            {
                                "count": len(result.evidence_requirements),
                                "readiness": result.evidence_readiness_status,
                            },
                        )
                    )
                if result.extension_candidate_id:
                    events.append(
                        (
                            "extension_candidate_creation",
                            {"extension_candidate_id": result.extension_candidate_id},
                        )
                    )
                if not result.resolved:
                    events.append(
                        (
                            "unresolved_metric_handling",
                            {"mapping_status": result.mapping_status},
                        )
                    )

                for activity, outputs in events:
                    prov.record_activity(
                        entity_type="orchestrator_result",
                        entity_id=entity_id,
                        activity=activity,
                        agent="registry_orchestrator",
                        method="RegistryOrchestratorService.process",
                        inputs={"raw_metric_name": result.raw_metric_name},
                        outputs=outputs,
                        confidence=result.mapping_confidence,
                    )
            except Exception as exc:
                logger.warning("provenance recording failed: %s", exc)
                gov_warnings.append(f"provenance recording failed: {exc}")

        result.governance_warnings = gov_warnings
        result.governance_errors = gov_errors
        result.review_required = review_required
        # Merge into general warnings/errors without replacing existing
        for w in gov_warnings:
            if w not in result.warnings:
                result.warnings.append(w)
        for e in gov_errors:
            if e not in result.errors:
                result.errors.append(e)

    def _attach_lifecycle_and_standards(
        self,
        result: OrchestratorResult,
        *,
        attach_lifecycle: bool,
        attach_standards: bool,
    ) -> None:
        """Soft lifecycle/standards enrichment — never changes ``resolved``."""
        if self._session is None or not result.cim_namespace:
            if attach_standards and not result.standards_mappings:
                result.no_direct_standard_match = True
            return

        allow_approved_standards = (
            result.resolved
            and (result.mapping_status or "").lower() in _APPROVED_STATUSES
            and not result.fallback_used
            and not result.candidate_flags.get("metric_unresolved")
            and not result.candidate_flags.get("mapping_candidate")
        )

        if attach_lifecycle:
            try:
                from cloud_metrics.registry.lifecycle import LifecycleRegistryService

                life = LifecycleRegistryService(session=self._session)
                life_res = life.get_links_for_metric(
                    result.cim_namespace,
                    metric_id=result.metric_definition_id,
                )
                result.lifecycle_links = list(life_res.links)
                result.lifecycle_stages = list(life_res.stages)
                result.lifecycle_usage_purposes = list(life_res.usage_purposes)
                result.lifecycle_importance = list(life_res.importance)
                result.lifecycle_review_status = list(life_res.review_statuses)
                logger.info(
                    "lifecycle enrichment: ns=%s stages=%s",
                    result.cim_namespace,
                    result.lifecycle_stages,
                )
            except Exception as exc:
                logger.warning("lifecycle enrichment failed: %s", exc)
                result.warnings.append(f"lifecycle enrichment failed: {exc}")

        if attach_standards:
            try:
                from cloud_metrics.registry.standards import StandardsRegistryService

                std = StandardsRegistryService(session=self._session)
                std_res = std.get_mappings_for_metric(
                    result.cim_namespace,
                    metric_id=result.metric_definition_id,
                    allow_approved=allow_approved_standards,
                )
                result.standards_mappings = list(std_res.mappings)
                result.standards_relation_types = list(std_res.relation_types)
                result.standards_confidence_scores = list(std_res.confidence_scores)
                result.standards_review_status = list(std_res.review_statuses)
                result.standards_notes = list(std_res.notes)
                result.no_direct_standard_match = bool(std_res.no_direct_standard_match)
                logger.info(
                    "standards enrichment: ns=%s relations=%s no_direct=%s approved=%s",
                    result.cim_namespace,
                    result.standards_relation_types,
                    result.no_direct_standard_match,
                    allow_approved_standards,
                )
            except Exception as exc:
                logger.warning("standards enrichment failed: %s", exc)
                result.warnings.append(f"standards enrichment failed: {exc}")
                result.no_direct_standard_match = True

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
            if mapping_status in {"approved", "active"}:
                mapping_status = "unresolved"

        metric_definition_id = None
        confidence = None
        relation_type = None
        if lookup.mapping is not None:
            metric_definition_id = lookup.mapping.cim_metric_id
            confidence = lookup.mapping.confidence
            relation_type = lookup.mapping.relation_type

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
            no_direct_standard_match=True,
        )


def get_registry_orchestrator(
    session: Optional[Session] = None,
) -> RegistryOrchestratorService:
    return RegistryOrchestratorService(session=session)


CimRegistryOrchestrator = RegistryOrchestratorService
RegistryOrchestrator = RegistryOrchestratorService
