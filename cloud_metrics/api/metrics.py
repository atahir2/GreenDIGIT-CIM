from fastapi import APIRouter, HTTPException
from cloud_metrics.ingestion.aws import ingest_aws_metrics
from cloud_metrics.ingestion.gcp import ingest_gcp_metrics

router = APIRouter()

@router.get("/aws")
async def ingest_aws():
    try:
        ingest_aws_metrics()
        return {"status": "aws metrics ingested"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/gcp")
async def ingest_gcp():
    try:
        ingest_gcp_metrics()
        return {"status": "gcp metrics ingested"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
