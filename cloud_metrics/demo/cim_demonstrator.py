"""Milestone 10 — registry-driven CIM end-to-end demonstrator helpers.

Loads realistic sample fixtures, ensures demo raw→CIM mappings exist in the
session, and runs ``RegistryOrchestratorService.process`` for each metric.
Does not replace ingestion; does not remove legacy fallback.
"""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from sqlalchemy.orm import Session

from cloud_metrics.models.cim_registry import CimMetricDefinition, CimMetricMapping
from cloud_metrics.registry.orchestrator import (
    OrchestratorResult,
    RawMetricContext,
    get_registry_orchestrator,
)

# Project-root-relative fixtures (used by script + tests)
FIXTURE_DIR = (
    Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "cim_demo"
)

# Approved raw keys used by demo samples → seeded CIM namespaces.
# Unknown/extension metrics intentionally omitted.
DEMO_RAW_TO_CIM: Dict[str, str] = {
    "node_power_watts": "cim:compute.node.power.draw",
    "gpu_avg_power": "cim:compute.gpu.power.average",
    "cpu_utilisation": "cim:compute.cpu.utilisation",
    "memory_used": "cim:compute.memory.usage",
    "network_ingress": "cim:network.traffic.ingress",
    "energy_consumption": "cim:energy.consumption.total",
    "carbon_intensity": "cim:carbon.intensity.location_based",
    "workflow_execution_duration": "cim:workflow.execution.duration",
    "workflow_energy_per_run": "cim:workflow.energy.per_run",
    "workflow_carbon_per_run": "cim:workflow.carbon.per_run",
    "total_facility_energy": "cim:facility.energy.consumption.total",
    "it_equipment_energy": "cim:facility.it.energy.consumption",
    "water_usage_total": "cim:water.usage.total",
    "carbon_emission_operational": "cim:carbon.emission.operational",
    "energy_efficiency_pue": "cim:energy.efficiency.pue",
}

SAMPLE_FILES: Dict[str, str] = {
    "A": "known_metrics_sample.json",
    "B": "wrong_units_sample.json",
    "C": "workflow_run_metrics_sample.json",
    "D": "facility_kpi_sample.json",
    "E": "unknown_metrics_sample.json",
}

UNSTRUCTURED_SAMPLE = "unstructured_metrics_sample.txt"


def fixture_path(name: str) -> Path:
    return FIXTURE_DIR / name


def load_sample(name: str) -> Dict[str, Any]:
    path = fixture_path(name)
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def load_unstructured_sample() -> str:
    return fixture_path(UNSTRUCTURED_SAMPLE).read_text(encoding="utf-8")


def ensure_demo_mappings(session: Session) -> int:
    """Idempotently create approved mappings for demo raw keys. Returns created count."""
    created = 0
    for raw_key, namespace in DEMO_RAW_TO_CIM.items():
        metric = (
            session.query(CimMetricDefinition).filter_by(namespace=namespace).one_or_none()
        )
        if metric is None:
            continue
        existing = (
            session.query(CimMetricMapping)
            .filter_by(source_key=raw_key, source_id=None)
            .first()
        )
        if existing is not None:
            continue
        session.add(
            CimMetricMapping(
                source_key=raw_key,
                source_id=None,
                metric_id=metric.id,
                relation_type="exactMatch",
                origin="demo",
                status="approved",
                review_status="approved",
                confidence_score=1.0,
                version=1,
                created_by="milestone10_cim_demo",
                notes=f"Demo mapping {raw_key} → {namespace}",
            )
        )
        created += 1
    if created:
        session.commit()
    return created


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


def sample_to_contexts(sample: Mapping[str, Any]) -> List[RawMetricContext]:
    """Convert a fixture sample document into orchestrator contexts."""
    ctx = dict(sample.get("context") or {})
    source = ctx.get("source")
    source_type = ctx.get("source_type")
    source_metadata = dict(ctx.get("source_metadata") or {})
    asset_labels = dict(ctx.get("asset_labels") or {})
    timestamp = _parse_timestamp(ctx.get("timestamp"))
    aggregation_period = ctx.get("aggregation_period")
    boundary = ctx.get("boundary")
    formula = ctx.get("formula_or_derivation_method")
    workflow_id = ctx.get("workflow_id")
    run_id = ctx.get("run_id") or ctx.get("workflow_run_id")

    # Flatten useful context into original_raw_metadata for extractors / rules
    original: Dict[str, Any] = {
        k: v
        for k, v in ctx.items()
        if k
        not in {
            "source_metadata",
            "asset_labels",
            "time_window",
            "reporting_period",
        }
    }
    for k, v in asset_labels.items():
        original.setdefault(k, v)
    if workflow_id:
        original.setdefault("workflow_id", workflow_id)
    if run_id:
        original.setdefault("run_id", run_id)
        original.setdefault("workflow_run_id", run_id)

    contexts: List[RawMetricContext] = []
    for metric in sample.get("metrics") or []:
        name = metric["name"]
        contexts.append(
            RawMetricContext(
                raw_metric_name=name,
                value=metric.get("value"),
                unit=metric.get("unit"),
                timestamp=timestamp,
                source=source,
                source_type=source_type,
                source_metadata=source_metadata or None,
                asset_labels=asset_labels or None,
                original_raw_metadata=dict(original),
                aggregation_period=aggregation_period,
                boundary=boundary,
                formula_or_derivation_method=formula,
                workflow_id=workflow_id,
                run_id=run_id,
            )
        )
    return contexts


def result_to_dict(result: OrchestratorResult) -> Dict[str, Any]:
    """Serialize orchestrator result for printing / snapshots."""
    return result.to_metadata()


def _json_default(obj: Any) -> Any:
    if is_dataclass(obj):
        return asdict(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, Path):
        return str(obj)
    return str(obj)


def format_result_summary(result: OrchestratorResult) -> str:
    lines = [
        f"raw={result.raw_metric_name}",
        f"  cim_namespace={result.cim_namespace}",
        f"  resolved={result.resolved} path={result.resolution_path} "
        f"status={result.mapping_status} fallback={result.fallback_used}",
        f"  unit={result.observed_unit} -> {result.unit_validation_status} "
        f"(expected {result.expected_quantity_kind}/{result.canonical_unit})",
        f"  source={result.source_resolution_status} id={result.source_id}",
        f"  asset={result.asset_resolution_status} id={result.asset_id}",
        f"  lifecycle={result.lifecycle_stages}",
        f"  standards_relations={result.standards_relation_types}",
        f"  evidence_readiness={result.evidence_readiness_status} "
        f"n_req={len(result.evidence_requirements)}",
        f"  provenance={result.provenance_log_reference}",
        f"  extension_candidate_id={result.extension_candidate_id}",
        f"  review_required={result.review_required}",
    ]
    if result.validation_results:
        failed = [v for v in result.validation_results if not v.passed]
        lines.append(
            f"  rules: total={len(result.validation_results)} failed={len(failed)}"
        )
        for v in failed[:5]:
            lines.append(f"    - [{v.severity}] {v.rule_name}: {v.message}")
    if result.warnings:
        lines.append(f"  warnings={result.warnings[:5]}")
    if result.errors:
        lines.append(f"  errors={result.errors[:5]}")
    return "\n".join(lines)


def process_contexts(
    session: Session,
    contexts: Sequence[RawMetricContext],
    **orch_kwargs: Any,
) -> List[OrchestratorResult]:
    orch = get_registry_orchestrator(session)
    return [orch.process(ctx, **orch_kwargs) for ctx in contexts]


def process_sample(
    session: Session,
    sample: Mapping[str, Any],
    **orch_kwargs: Any,
) -> List[OrchestratorResult]:
    return process_contexts(session, sample_to_contexts(sample), **orch_kwargs)


def prepare_pue_context(sample: Mapping[str, Any]) -> Optional[RawMetricContext]:
    """Build a RawMetricContext for prepared PUE evidence lookup (no calc engine)."""
    prep = sample.get("pue_preparation")
    if not prep:
        return None
    ctx = dict(sample.get("context") or {})
    metrics = {m["name"]: m for m in sample.get("metrics") or []}
    num = metrics.get(prep.get("numerator_metric") or "")
    den = metrics.get(prep.get("denominator_metric") or "")
    value = prep.get("prepared_pue_value")
    if value is None and num and den and den.get("value"):
        value = float(num["value"]) / float(den["value"])
    return RawMetricContext(
        raw_metric_name=prep.get("raw_metric_name_for_evidence", "energy_efficiency_pue"),
        value=value,
        unit=prep.get("prepared_pue_unit", "ratio"),
        timestamp=_parse_timestamp(ctx.get("timestamp")),
        source=ctx.get("source"),
        source_type=ctx.get("source_type"),
        asset_labels=dict(ctx.get("asset_labels") or {}) or None,
        original_raw_metadata={
            "aggregation_period": ctx.get("aggregation_period"),
            "boundary": ctx.get("boundary"),
            "formula_or_derivation_method": "facility_energy / it_energy",
            "pue_inputs_prepared": True,
            "numerator": num,
            "denominator": den,
        },
        aggregation_period=ctx.get("aggregation_period"),
        boundary=ctx.get("boundary"),
        formula_or_derivation_method="facility_energy / it_energy",
    )


def run_scenario(
    session: Session,
    scenario_key: str,
    *,
    ensure_mappings: bool = True,
) -> Dict[str, Any]:
    """Run one lettered scenario (A–E) and return a structured report.

    Scenario E disables legacy fallback so fuzzy alias matches (e.g. ``work``
    inside ``workflow_green_score``) cannot silently assign a CIM namespace.
    Extension candidates are created instead. Legacy fallback remains enabled
    for scenarios A–D and is covered by dedicated tests.
    """
    if ensure_mappings:
        ensure_demo_mappings(session)

    key = scenario_key.upper()
    if key not in SAMPLE_FILES:
        raise ValueError(f"Unknown scenario {scenario_key!r}; expected one of {list(SAMPLE_FILES)}")

    sample = load_sample(SAMPLE_FILES[key])
    orch_kwargs: Dict[str, Any] = {}
    if key == "E":
        orch_kwargs = {
            "use_fallback": False,
            "create_candidate_on_fallback": False,
            "create_extension_on_unresolved": True,
        }
    results = process_sample(session, sample, **orch_kwargs)
    report: Dict[str, Any] = {
        "scenario": key,
        "fixture": SAMPLE_FILES[key],
        "description": sample.get("description"),
        "results": [result_to_dict(r) for r in results],
        "summaries": [format_result_summary(r) for r in results],
        "orchestrator_results": results,
    }

    if key == "D":
        pue_ctx = prepare_pue_context(sample)
        if pue_ctx is not None:
            pue_result = get_registry_orchestrator(session).process(pue_ctx)
            report["pue_preparation"] = {
                "prepared_value": pue_ctx.value,
                "unit": pue_ctx.unit,
                "result": result_to_dict(pue_result),
                "summary": format_result_summary(pue_result),
            }
            report["pue_orchestrator_result"] = pue_result

    return report


def run_all_scenarios(session: Session) -> Dict[str, Any]:
    ensure_demo_mappings(session)
    scenarios = {k: run_scenario(session, k, ensure_mappings=False) for k in SAMPLE_FILES}
    unstructured: Optional[Dict[str, Any]] = None
    try:
        from cloud_metrics.parsers.unstructured_parser import parse_unstructured_text

        text = load_unstructured_sample()
        extracted = parse_unstructured_text(text, datacenter="RI-site-1")
        unstructured = {"extracted": extracted, "note": "parser exists; not orchestrated"}
    except Exception as exc:  # pragma: no cover - optional path
        unstructured = {"error": str(exc)}

    return {
        "scenarios": scenarios,
        "unstructured": unstructured,
        "fixture_dir": str(FIXTURE_DIR),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def _strip_live_results(obj: Any) -> Any:
    """Drop live OrchestratorResult objects before JSON serialization."""
    skip = {"orchestrator_results", "pue_orchestrator_result"}
    if isinstance(obj, dict):
        return {
            k: _strip_live_results(v)
            for k, v in obj.items()
            if k not in skip
        }
    if isinstance(obj, list):
        return [_strip_live_results(v) for v in obj]
    return obj


def dumps_report(report: Mapping[str, Any], *, indent: int = 2) -> str:
    """JSON-serialize a report, dropping live OrchestratorResult objects."""
    return json.dumps(_strip_live_results(dict(report)), indent=indent, default=_json_default)


def critical_rule_failures(result: OrchestratorResult) -> List[str]:
    return [
        v.rule_name
        for v in result.validation_results
        if (not v.passed) and v.severity in {"error", "critical"}
    ]


def iter_primary_results(
    report: Mapping[str, Any],
) -> Iterable[Tuple[str, OrchestratorResult]]:
    for r in report.get("orchestrator_results") or []:
        yield report["scenario"], r
    pue = report.get("pue_orchestrator_result")
    if pue is not None:
        yield "D_pue", pue
