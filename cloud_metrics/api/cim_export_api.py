# cloud_metrics/api/cim_export_api.py
"""CIM export / interoperability API (Milestone 15) — additive; read-only."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field

from cloud_metrics.registry.export import (
    DcatExportRequest,
    WorkflowRunExportRequest,
    get_export_service,
)
from cloud_metrics.utils.config import SessionLocal

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class WorkflowRunBody(BaseModel):
    workflow_id: str
    workflow_run_id: str
    energy_per_run: Optional[float] = None
    energy_unit: str = "kWh"
    carbon_per_run: Optional[float] = None
    carbon_unit: str = "kgCO2e"
    duration_seconds: Optional[float] = None
    input_refs: List[str] = Field(default_factory=list)
    output_refs: List[str] = Field(default_factory=list)
    source: Optional[str] = None
    asset: Optional[str] = None
    resource: Optional[str] = None
    publisher: Optional[str] = None
    temporal_start: Optional[str] = None
    temporal_end: Optional[str] = None


class DcatBody(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    publisher: Optional[str] = None
    access_endpoint: Optional[str] = None
    dataset_kind: str = "metric_catalogue"
    temporal_start: Optional[str] = None
    temporal_end: Optional[str] = None


@router.get("/json")
def export_json(db=Depends(get_db)):
    return get_export_service(db).export_json()


@router.get("/csv/{dataset}")
def export_csv(dataset: str, db=Depends(get_db)):
    svc = get_export_service(db)
    try:
        text = svc.export_csv(dataset)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return Response(content=text, media_type="text/csv")


@router.get("/jsonld")
def export_jsonld(
    namespace: Optional[str] = Query(default=None),
    all_metrics: bool = Query(default=False),
    db=Depends(get_db),
):
    return get_export_service(db).export_jsonld(
        metric_namespace=namespace,
        include_all_metrics=all_metrics,
    )


@router.post("/rocrate-style")
def export_rocrate(body: WorkflowRunBody, db=Depends(get_db)):
    req = WorkflowRunExportRequest(**body.model_dump())
    return get_export_service(db).export_rocrate_style(req)


@router.get("/dcat-style")
def export_dcat(
    title: Optional[str] = None,
    publisher: Optional[str] = None,
    access_endpoint: Optional[str] = None,
    db=Depends(get_db),
):
    req = DcatExportRequest(
        title=title, publisher=publisher, access_endpoint=access_endpoint
    )
    return get_export_service(db).export_dcat_style(req)


@router.post("/dcat-style")
def export_dcat_post(body: DcatBody, db=Depends(get_db)):
    req = DcatExportRequest(**body.model_dump())
    return get_export_service(db).export_dcat_style(req)


@router.get("/standards-crosswalk")
def export_crosswalk(db=Depends(get_db)):
    return get_export_service(db).export_standards_crosswalk()


@router.get("/evidence-readiness")
def export_evidence(
    namespace: Optional[str] = Query(default=None),
    db=Depends(get_db),
):
    return get_export_service(db).export_evidence_readiness(metric_namespace=namespace)


@router.get("/provenance")
def export_provenance(
    entity_type: Optional[str] = Query(default=None),
    entity_id: Optional[int] = Query(default=None),
    db=Depends(get_db),
):
    return get_export_service(db).export_provenance(
        entity_type=entity_type, entity_id=entity_id
    )
