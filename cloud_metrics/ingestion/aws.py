from cloud_metrics.ingestion.realtime_ingestor import ingest_from_api

def fetch_from_aws() -> dict:
    # Replace with real AWS fetch; these keys match metric_mapping.json
    return {"CPUUtilization": 12.3, "FreeableMemory": 2048}

def ingest_aws_metrics() -> None:
    raw = fetch_from_aws()
    ingest_from_api(raw, "aws", uploaded_by="system")
