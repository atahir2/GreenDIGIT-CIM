# cloud_metrics/api/query.py

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict

from cloud_metrics.services.influx_service import query_metrics

router = APIRouter()

class QueryResponse(BaseModel):
    _time: str
    _value: float
    model_config = ConfigDict(extra="allow")  # pydantic v2

@router.get(
    "/",
    response_model=List[QueryResponse],
    summary="Query metrics from InfluxDB",
    description=(
        "Fetch data points for a given measurement name within the specified time range. "
        "Add any number of tag filters as query params (e.g., ?region=eu-west)."
    ),
)
async def query_endpoint(
    request: Request,
    measurement: str = Query(..., description="Measurement name to query"),
    start: str = Query("-1h", description="Flux range start"),
    stop: Optional[str] = Query(None, description="Flux range stop"),
) -> Any:
    try:
        # derive filters from query params
        filters: Dict[str, str] = {
            k: v for k, v in request.query_params.multi_items()
            if k not in ("measurement", "start", "stop")
        }
        result = query_metrics(measurement=measurement, start=start, stop=stop, **filters)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {e}")
