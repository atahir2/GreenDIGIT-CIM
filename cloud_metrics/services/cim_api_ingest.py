# cloud_metrics/services/cim_api_ingest.py
"""External organization / RI API ingestion via Registry Orchestrator (MS16C).

Uses the same orchestrator path as the Milestone 10 demonstrator. Does not
approve unknown metrics. Optional sample persistence and KPI calculation are
additive and do not change browser/UI callers.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence

from sqlalchemy.orm import Session

from cloud_metrics.demo.cim_demonstrator import (
    ensure_demo_mappings,
    result_to_dict,
)
from cloud_metrics.registry.kpi import KpiInput, get_kpi_calculation_service
from cloud_metrics.registry.orchestrator import (
    OrchestratorResult,
    RawMetricContext,
    get_registry_orchestrator,
)


def _parse_timestamp(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def build_contexts_from_payload(payload: Dict[str, Any]) -> List[RawMetricContext]:
    """Normalize an external API payload into orchestrator contexts."""
    organization_id = payload.get("organization_id") or payload.get("organization")
    source = payload.get("source") or payload.get("source_identifier")
    source_type = payload.get("source_type") or "api"
    source_metadata = dict(payload.get("source_metadata") or {})
    if organization_id:
        source_metadata.setdefault("organization_id", organization_id)
    source_metadata.setdefault("ingestion_method", "api")

    asset = dict(payload.get("asset") or payload.get("asset_labels") or {})
    resource = dict(payload.get("resource") or payload.get("resource_metadata") or {})
    for k, v in resource.items():
        asset.setdefault(k, v)

    workflow_id = payload.get("workflow_id")
    run_id = payload.get("run_id") or payload.get("workflow_run_id")
    aggregation_period = payload.get("aggregation_period")
    boundary = payload.get("boundary") or payload.get("reporting_boundary")
    formula = payload.get("formula_or_derivation_method") or payload.get("formula")
    timestamp = _parse_timestamp(payload.get("timestamp") or payload.get("captured_at"))

    original: Dict[str, Any] = {
        "organization_id": organization_id,
        "ingestion_path": "cim_api_ingest",
    }
    for k, v in asset.items():
        original.setdefault(k, v)
    if workflow_id:
        original["workflow_id"] = workflow_id
    if run_id:
        original["run_id"] = run_id
        original["workflow_run_id"] = run_id
    if aggregation_period:
        original["aggregation_period"] = aggregation_period
    if boundary:
        original["boundary"] = boundary
    if formula:
        original["formula_or_derivation_method"] = formula
    for k, v in (payload.get("extra") or {}).items():
        original.setdefault(k, v)

    contexts: List[RawMetricContext] = []
    for metric in payload.get("metrics") or []:
        name = metric.get("name") or metric.get("raw_metric_name") or metric.get("raw_key")
        if not name:
            continue
        contexts.append(
            RawMetricContext(
                raw_metric_name=str(name),
                value=metric.get("value"),
                unit=metric.get("unit"),
                timestamp=timestamp,
                source=source,
                source_type=source_type,
                source_metadata=source_metadata or None,
                asset_labels=asset or None,
                original_raw_metadata=dict(original),
                aggregation_period=aggregation_period,
                boundary=boundary,
                formula_or_derivation_method=formula,
                workflow_id=workflow_id,
                run_id=run_id,
            )
        )
    return contexts


def _critical_failures(result: OrchestratorResult) -> List[str]:
    out: List[str] = []
    for v in result.validation_results or []:
        if (not v.passed) and v.severity in {"error", "critical"}:
            out.append(v.rule_name or v.message or "rule_failed")
    if (result.unit_validation_status or "").lower() in {
        "incompatible",
        "invalid",
        "conflict",
    }:
        out.append(f"unit_{result.unit_validation_status}")
    out.extend(result.errors or [])
    return out


def _result_row(result: OrchestratorResult) -> Dict[str, Any]:
    meta = result_to_dict(result)
    meta["observed_value"] = None
    # value lives on context, not always in metadata — attach from result if present
    # OrchestratorResult does not store value; caller may enrich
    meta["critical_issues"] = _critical_failures(result)
    meta["accepted_as_valid"] = not bool(meta["critical_issues"]) and bool(result.resolved)
    return meta


def _maybe_calculate_kpi(
    session: Session,
    payload: Dict[str, Any],
    options: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    kpi = (options.get("calculate_kpi") or "").strip().lower()
    if not kpi:
        return None
    by_name = {
        (m.get("name") or m.get("raw_metric_name") or ""): m
        for m in (payload.get("metrics") or [])
    }
    svc = get_kpi_calculation_service(session)
    common = dict(
        aggregation_period=payload.get("aggregation_period"),
        boundary=payload.get("boundary") or payload.get("reporting_boundary"),
        allow_candidate_inputs=bool(options.get("allow_candidate_inputs")),
        source=payload.get("source"),
    )

    def _inp(key: str, default_name: str) -> Dict[str, Any]:
        m = by_name.get(key) or {}
        return {
            "name": default_name,
            "value": m.get("value"),
            "unit": m.get("unit"),
        }

    if kpi == "pue":
        result = svc.calculate_pue(
            _inp("total_facility_energy", "total_facility_energy"),
            _inp("it_equipment_energy", "it_equipment_energy"),
            **common,
        )
    elif kpi == "wue":
        result = svc.calculate_wue(
            _inp("water_usage_total", "water_usage_total"),
            _inp("it_equipment_energy", "it_equipment_energy"),
            **common,
        )
    elif kpi == "cue":
        result = svc.calculate_cue(
            _inp("carbon_emission_operational", "carbon_emission_operational"),
            _inp("it_equipment_energy", "it_equipment_energy"),
            **common,
        )
    else:
        return {"error": f"unsupported kpi '{kpi}'"}
    return result.to_dict()


def ingest_external_payload(
    session: Session,
    payload: Dict[str, Any],
    *,
    options: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Run Registry Orchestrator over an external org/RI metric payload.

    Returns a response dict suitable for FastAPI JSON. Never auto-approves
    unresolved / extension metrics.
    """
    opts = dict(options or {})
    ensure_mappings = opts.get("ensure_demo_mappings", True)
    if ensure_mappings:
        ensure_demo_mappings(session)

    contexts = build_contexts_from_payload(payload)
    if not contexts:
        return {
            "status": "rejected",
            "error": "no metrics provided",
            "organization_id": payload.get("organization_id"),
            "metrics_processed": 0,
            "results": [],
        }

    # Scenario E style: disable legacy fallback so unknowns become extensions
    use_fallback = opts.get("use_fallback", True)
    create_extension = opts.get("create_extension_on_unresolved", True)
    orch_kwargs = {
        "use_fallback": bool(use_fallback),
        "create_candidate_on_fallback": bool(opts.get("create_candidate_on_fallback", True)),
        "create_extension_on_unresolved": bool(create_extension),
        "create_source_candidate": bool(opts.get("create_source_candidate", True)),
        "create_asset_candidate": bool(opts.get("create_asset_candidate", True)),
    }

    orch = get_registry_orchestrator(session)
    live_results: List[OrchestratorResult] = []
    rows: List[Dict[str, Any]] = []
    for ctx in contexts:
        result = orch.process(ctx, **orch_kwargs)
        live_results.append(result)
        row = _result_row(result)
        row["observed_value"] = ctx.value
        row["observed_unit"] = ctx.unit
        rows.append(row)

    # Optional: also persist via the same process_metric_sample path used by UI
    persist = opts.get("persist_samples", False)
    persisted: List[Dict[str, Any]] = []
    if persist:
        from cloud_metrics.ingestion.automated_mapper import process_metric_sample

        origin = (
            payload.get("organization_id")
            or (payload.get("asset") or {}).get("site")
            or payload.get("source")
            or "api_org"
        )
        asset = payload.get("asset") or payload.get("asset_labels") or {}
        for ctx, orch_row in zip(contexts, rows):
            try:
                unified = process_metric_sample(
                    raw_key=ctx.raw_metric_name,
                    value=float(ctx.value) if ctx.value is not None else 0.0,
                    origin=str(origin),
                    captured_at=ctx.timestamp,
                    ri_id=asset.get("ri_id"),
                    node_id=asset.get("node") or asset.get("node_id"),
                    vm_id=asset.get("vm_id"),
                    host=asset.get("host"),
                    site_id=asset.get("site") or asset.get("site_id"),
                    domain=payload.get("domain"),
                    observed_unit=ctx.unit,
                    use_registry_orchestrator=True,
                    registry_session=session,
                    extra_meta={
                        "ingestion_path": "cim_api_ingest",
                        "organization_id": payload.get("organization_id"),
                        "source": ctx.source,
                        "source_type": ctx.source_type,
                        "workflow_id": ctx.workflow_id,
                        "run_id": ctx.run_id,
                        "aggregation_period": ctx.aggregation_period,
                        "boundary": ctx.boundary,
                    },
                )
                persisted.append(
                    {
                        "raw_key": ctx.raw_metric_name,
                        "unified_key": unified,
                        "value": ctx.value,
                    }
                )
            except Exception as exc:
                persisted.append(
                    {
                        "raw_key": ctx.raw_metric_name,
                        "error": str(exc),
                    }
                )

    kpi_result = None
    try:
        kpi_result = _maybe_calculate_kpi(session, payload, opts)
    except Exception as exc:
        kpi_result = {"error": str(exc)}

    session.commit()

    critical_count = sum(1 for r in rows if r.get("critical_issues"))
    unresolved = sum(1 for r in rows if not r.get("resolved"))
    status = "accepted"
    if critical_count and unresolved == 0:
        status = "accepted_with_validation_issues"
    elif unresolved:
        status = "accepted_with_candidates"

    return {
        "status": status,
        "organization_id": payload.get("organization_id"),
        "source": payload.get("source"),
        "source_type": payload.get("source_type"),
        "timestamp": (
            contexts[0].timestamp.isoformat() if contexts[0].timestamp else None
        ),
        "metrics_processed": len(rows),
        "resolved_count": sum(1 for r in rows if r.get("resolved")),
        "unresolved_count": unresolved,
        "validation_issue_count": critical_count,
        "results": rows,
        "persisted_samples": persisted if persist else None,
        "kpi": kpi_result,
        "orchestrator": "RegistryOrchestratorService",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "notes": [
            "Unknown metrics are never auto-approved.",
            "Unit incompatibilities are reported; soft validation does not hard-block sample acceptance.",
            "Reportable KPI calculation (when requested) does hard-block missing/incompatible inputs.",
        ],
    }


def summarize_results(results: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "count": len(results),
        "namespaces": sorted(
            {r.get("cim_namespace") for r in results if r.get("cim_namespace")}
        ),
        "unit_statuses": sorted(
            {
                r.get("unit_validation_status")
                for r in results
                if r.get("unit_validation_status")
            }
        ),
        "extension_ids": [
            r.get("extension_candidate_id")
            for r in results
            if r.get("extension_candidate_id") is not None
        ],
    }
