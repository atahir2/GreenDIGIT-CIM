# cloud_metrics/api/cim_ingest_api.py
"""CIM external organization / RI metric ingest API (Milestone 16C).

Additive FastAPI router. Uses ``RegistryOrchestratorService`` via
``cloud_metrics.services.cim_api_ingest``. Does not replace legacy
``/metrics/aws`` / ``/metrics/gcp`` triggers. Does not auto-approve unknowns.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from cloud_metrics.services.cim_api_ingest import ingest_external_payload
from cloud_metrics.utils.config import SessionLocal

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class MetricIn(BaseModel):
    name: str = Field(..., description="Raw metric name from the external system")
    value: Optional[float] = None
    unit: Optional[str] = None
    raw_metric_name: Optional[str] = None  # alias accepted by service if name omitted


class IngestOptions(BaseModel):
    ensure_demo_mappings: bool = True
    use_fallback: bool = True
    create_candidate_on_fallback: bool = True
    create_extension_on_unresolved: bool = True
    create_source_candidate: bool = True
    create_asset_candidate: bool = True
    persist_samples: bool = False
    calculate_kpi: Optional[str] = Field(
        default=None, description="Optional pue|wue|cue after metric orchestration"
    )
    allow_candidate_inputs: bool = False


class ExternalIngestBody(BaseModel):
    organization_id: Optional[str] = Field(
        default=None, description="External organization or RI identifier"
    )
    source: Optional[str] = Field(
        default=None, description="Source system name / identifier"
    )
    source_type: Optional[str] = Field(
        default="api", description="e.g. monitoring_system, workflow_instrumentation"
    )
    source_identifier: Optional[str] = None
    timestamp: Optional[str] = None
    captured_at: Optional[str] = None
    aggregation_period: Optional[str] = None
    boundary: Optional[str] = None
    reporting_boundary: Optional[str] = None
    workflow_id: Optional[str] = None
    run_id: Optional[str] = None
    workflow_run_id: Optional[str] = None
    formula_or_derivation_method: Optional[str] = None
    domain: Optional[str] = None
    source_metadata: Dict[str, Any] = Field(default_factory=dict)
    asset: Dict[str, Any] = Field(default_factory=dict)
    asset_labels: Dict[str, Any] = Field(default_factory=dict)
    resource: Dict[str, Any] = Field(default_factory=dict)
    resource_metadata: Dict[str, Any] = Field(default_factory=dict)
    extra: Dict[str, Any] = Field(default_factory=dict)
    metrics: List[MetricIn] = Field(default_factory=list)
    options: IngestOptions = Field(default_factory=IngestOptions)


@router.post("/metrics")
def ingest_metrics(body: ExternalIngestBody, db=Depends(get_db)):
    """Ingest external metric payloads through the Registry Orchestrator.

    Returns per-metric CIM namespace, unit validation, source/asset resolution,
    lifecycle/standards, evidence, provenance, and extension candidate ids.
    Unknown metrics remain candidate / under_review — never silently approved.
    """
    if not body.metrics:
        raise HTTPException(status_code=400, detail="metrics list is required")
    payload = body.model_dump()
    options = payload.pop("options") or {}
    # Normalize name alias
    for m in payload.get("metrics") or []:
        if not m.get("name") and m.get("raw_metric_name"):
            m["name"] = m["raw_metric_name"]
    try:
        return ingest_external_payload(db, payload, options=options)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/scenarios/{scenario}")
def ingest_scenario(scenario: str, db=Depends(get_db)):
    """Convenience: run demo fixture scenario A–E through the API ingest path.

    Intended for integration validation / onboarding demos. Production
    organizations should POST ``/metrics`` with their own payloads.
    """
    from cloud_metrics.demo.cim_demonstrator import SAMPLE_FILES, load_sample

    key = scenario.strip().upper()
    if key not in SAMPLE_FILES:
        raise HTTPException(
            status_code=400,
            detail=f"scenario must be one of {sorted(SAMPLE_FILES)}",
        )
    sample = load_sample(SAMPLE_FILES[key])
    ctx = dict(sample.get("context") or {})
    payload: Dict[str, Any] = {
        "organization_id": f"demo-scenario-{key}",
        "source": ctx.get("source"),
        "source_type": ctx.get("source_type"),
        "source_metadata": dict(ctx.get("source_metadata") or {}),
        "asset": dict(ctx.get("asset_labels") or {}),
        "timestamp": ctx.get("timestamp"),
        "aggregation_period": ctx.get("aggregation_period"),
        "boundary": ctx.get("boundary"),
        "workflow_id": ctx.get("workflow_id"),
        "run_id": ctx.get("run_id") or ctx.get("workflow_run_id"),
        "formula_or_derivation_method": ctx.get("formula_or_derivation_method"),
        "metrics": [
            {
                "name": m.get("name"),
                "value": m.get("value"),
                "unit": m.get("unit"),
            }
            for m in (sample.get("metrics") or [])
        ],
    }
    options: Dict[str, Any] = {
        "ensure_demo_mappings": True,
        "persist_samples": False,
    }
    if key == "E":
        options.update(
            {
                "use_fallback": False,
                "create_candidate_on_fallback": False,
                "create_extension_on_unresolved": True,
            }
        )
    if key == "D":
        options["calculate_kpi"] = "pue"
    try:
        return ingest_external_payload(db, payload, options=options)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
