from datetime import datetime
from cloud_metrics.mapping.namespace_mapper import map_raw_to_unified
from cloud_metrics.services.influx_service import write_metrics

def fetch_from_gcp() -> dict:
    # Replace with real GCP fetch; example keys
    return {"CPU_UsagePercent": 8.9, "MemoryAvailableMB": 1024}

def ingest_gcp_metrics() -> None:
    raw = fetch_from_gcp()
    now = datetime.utcnow()
    batch = []
    for raw_key, val in raw.items():
        um = map_raw_to_unified(raw_key, val)
        if um:
            batch.append((um.name, float(val), um.tags, now))
    if batch:
        write_metrics(batch)
