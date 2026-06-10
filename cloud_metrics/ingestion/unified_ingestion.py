# cloud_metrics/ingestion/unified_ingestion.py

import os
from datetime import datetime

from cloud_metrics.mapping.namespace_mapper_core import parse_and_extract_file_metrics
from cloud_metrics.services.influx_service import write_mapped_metrics
from cloud_metrics.services.insert_file_upload_log import insert_file_upload_log
from cloud_metrics.services.insert_metric_definition import insert_metric_definition
from cloud_metrics.services.insert_datacenter import insert_datacenter
from cloud_metrics.ingestion.automated_mapper import process_metric_sample
from cloud_metrics.exporters.external_json import build_metadata, write_external_metrics_json


SUPPORTED_FILE_TYPES = [".json", ".xml", ".csv", ".yaml", ".txt"]

def ingest_from_file(
    file_path: str,
    datacenter_name: str,
    uploaded_by: str | None = None
):
    """
    Master ingestion: validate file type, ensure datacenter, parse & classify,
    write to InfluxDB, log the upload, and persist any new metric definitions.
    """
    ext = os.path.splitext(file_path)[1].lower()
    if ext not in SUPPORTED_FILE_TYPES:
        raise ValueError(f"Unsupported file type: {ext}")

    # Ensure datacenter is registered
    insert_datacenter(name=datacenter_name)

    # Parse raw metrics from the file
    print("Parsed file, now mapping metrics...")
    raw_metrics, _ = parse_and_extract_file_metrics(file_path, datacenter_name)
    print(f"Raw metrics: {list(raw_metrics.keys())}")

    origin = os.path.splitext(os.path.basename(file_path))[0]

    # Classify and map each raw metric
    new_mapped_metrics: dict[str, float] = {}

    for raw_key, value in raw_metrics.items():
        print(f"Classifying + mapping: {raw_key}")
        unified_key = process_metric_sample(
            raw_key=raw_key,
            value=float(value),
            origin=origin,
            captured_at=datetime.utcnow(),
        )
        new_mapped_metrics[unified_key] = value

    meta = build_metadata(
        ri_id="",
        node_id="",
        vm_id="",
        datacenter=origin,
        host="",
    )
    write_external_metrics_json(
        metadata=meta,
        metrics_unified_values=new_mapped_metrics,
        file_basename=origin,
    )

    # Write unified metrics to InfluxDB
    timestamp = datetime.utcnow()
    print("Writing to InfluxDB...")
    write_mapped_metrics(new_mapped_metrics, timestamp)

    # Record the file upload in your SQL logs
    insert_file_upload_log(
        filename=os.path.basename(file_path),
        datacenter_id=1,  # replace with actual lookup logic if needed
        uploaded_by=uploaded_by
    )

    # Persist any new unified metric definitions in PostgreSQL
    for unified_key in new_mapped_metrics:
        insert_metric_definition(unified_key=unified_key)

    print("Ingestion complete.")
