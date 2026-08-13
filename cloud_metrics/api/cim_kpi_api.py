# cloud_metrics/api/cim_kpi_api.py
"""CIM KPI Calculation API (Milestone 13) — additive; does not change ingestion."""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from cloud_metrics.registry.kpi import get_kpi_calculation_service
from cloud_metrics.utils.config import SessionLocal

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class KpiInputIn(BaseModel):
    name: Optional[str] = None
    value: Optional[float] = None
    unit: Optional[str] = None
    namespace: Optional[str] = None
    metric_status: Optional[str] = None
    mapping_status: Optional[str] = None


class KpiCalculateBody(BaseModel):
    aggregation_period: Optional[str] = None
    boundary: Optional[str] = None
    reportable: bool = True
    allow_candidate_inputs: bool = False
    source: Optional[str] = None
    total_facility_energy: Optional[KpiInputIn] = None
    it_equipment_energy: Optional[KpiInputIn] = None
    water_usage_total: Optional[KpiInputIn] = None
    carbon_emission_operational: Optional[KpiInputIn] = None
    carbon_intensity: Optional[KpiInputIn] = None
    carbon_kind: str = Field(default="emission")


def _dump(inp: Optional[KpiInputIn], default_name: str) -> Dict[str, Any]:
    if inp is None:
        raise HTTPException(status_code=400, detail=f"{default_name} is required")
    data = inp.model_dump()
    data["name"] = data.get("name") or default_name
    return data


@router.post("/{kpi}")
def calculate_kpi(kpi: str, body: KpiCalculateBody, db=Depends(get_db)):
    svc = get_kpi_calculation_service(db)
    common = dict(
        aggregation_period=body.aggregation_period,
        boundary=body.boundary,
        reportable=body.reportable,
        allow_candidate_inputs=body.allow_candidate_inputs,
        source=body.source,
    )
    try:
        key = kpi.strip().lower()
        if key == "pue":
            result = svc.calculate_pue(
                _dump(body.total_facility_energy, "total_facility_energy"),
                _dump(body.it_equipment_energy, "it_equipment_energy"),
                **common,
            )
        elif key == "wue":
            result = svc.calculate_wue(
                _dump(body.water_usage_total, "water_usage_total"),
                _dump(body.it_equipment_energy, "it_equipment_energy"),
                **common,
            )
        elif key == "cue":
            carbon = body.carbon_emission_operational or body.carbon_intensity
            name = (
                "carbon_intensity"
                if body.carbon_kind == "intensity"
                else "carbon_emission_operational"
            )
            result = svc.calculate_cue(
                _dump(carbon, name),
                _dump(body.it_equipment_energy, "it_equipment_energy"),
                carbon_kind=body.carbon_kind,
                **common,
            )
        else:
            raise HTTPException(status_code=400, detail="kpi must be pue, wue, or cue")
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.commit()
    return result.to_dict()
