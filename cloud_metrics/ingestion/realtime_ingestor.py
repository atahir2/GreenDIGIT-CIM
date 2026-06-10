# cloud_metrics/ingestion/realtime_ingestor.py

from datetime import datetime
from cloud_metrics.services.influx_service import write_mapped_metrics
from cloud_metrics.services.insert_metric_definition import insert_metric_definition
from cloud_metrics.services.insert_datacenter import get_or_create_datacenter_id
from cloud_metrics.services.insert_file_upload_log import insert_file_upload_log
from cloud_metrics.ingestion.automated_mapper import process_metric_sample

def ingest_from_api(
    metric_data: dict,
    datacenter_name: str,
    uploaded_by: str | None = None
):
    """
    Ingest real-time metric data from AWS, GCP, or other sources.
    :param metric_data: Raw dictionary of metrics (e.g., from cloud API)
    :param datacenter_name: Name of the cloud/datacenter provider
    :param uploaded_by: Optional user or system identifier
    """
    timestamp = datetime.utcnow()
    dc_id = get_or_create_datacenter_id(datacenter_name)

    # Classify, convert unit, validate, and persist each raw metric
    new_mapped_metrics: dict[str, float] = {}

    for raw_key, value in (metric_data or {}).items():
        unified_key = process_metric_sample(
            raw_key=raw_key,
            value=float(value),
            origin=datacenter_name,
            captured_at=timestamp,
        )
        new_mapped_metrics[unified_key] = float(value)

    # Write to InfluxDB
    if new_mapped_metrics:
        print("Writing to InfluxDB...")
        write_mapped_metrics(new_mapped_metrics, timestamp)

    # Log this ingestion as an API payload upload for audit
    insert_file_upload_log(
        filename=f"API-{datacenter_name}-{timestamp.isoformat()}",
        datacenter_id=dc_id,
        uploaded_by=uploaded_by
    )

    # Ensure any new unified keys exist in your SQL registry
    for unified_key in new_mapped_metrics:
        insert_metric_definition(unified_key=unified_key)

    print(f"✅ Real-time metrics ingested from {datacenter_name}.")
