from datetime import datetime
from cloud_metrics.mapping.namespace_mapper import map_raw_to_unified
from cloud_metrics.services.influx_service import write_metrics

def fetch_from_aws() -> dict:
    # Replace with real AWS fetch; these keys match metric_mapping.json
    return {"CPUUtilization": 12.3, "FreeableMemory": 2048}

def ingest_aws_metrics() -> None:
    raw = fetch_from_aws()
    now = datetime.utcnow()
    batch = []
    for raw_key, val in raw.items():
        um = map_raw_to_unified(raw_key, val)
        if um:
            batch.append((um.name, float(val), um.tags, now))
    if batch:
        write_metrics(batch)
