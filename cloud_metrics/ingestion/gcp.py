from cloud_metrics.ingestion.realtime_ingestor import ingest_from_api

def fetch_from_gcp() -> dict:
    # Replace with real GCP fetch; example keys
    return {"CPU_UsagePercent": 8.9, "MemoryAvailableMB": 1024}

def ingest_gcp_metrics() -> None:
    raw = fetch_from_gcp()
    ingest_from_api(raw, "gcp", uploaded_by="system")
