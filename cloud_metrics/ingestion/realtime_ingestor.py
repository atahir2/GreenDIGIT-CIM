# cloud_metrics/ingestion/realtime_ingestor.py

from datetime import datetime
from cloud_metrics.mapping.namespace_mapper_core import extract_metrics
from cloud_metrics.services.influx_service import write_metrics as write_mapped_metrics
from cloud_metrics.services.insert_metric_definition import insert_metric_definition
from cloud_metrics.services.insert_datacenter import insert_datacenter
from cloud_metrics.services.insert_file_upload_log import insert_file_upload_log

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

    # Map raw → unified using your namespace core logic
    mapped_metrics = extract_metrics(metric_data, datacenter_name)

    # Write to InfluxDB
    write_mapped_metrics(
        [(key, value, {}, timestamp) for key, value in mapped_metrics.items()]
    )

    # Optionally log this ingestion as a “file” upload for audit
    insert_file_upload_log(
        filename=f"API-{datacenter_name}-{timestamp.isoformat()}",
        datacenter_id=1,  # replace with lookup logic if you have datacenter table
        uploaded_by=uploaded_by
    )

    # Ensure any new unified keys exist in your SQL registry
    for unified_key in mapped_metrics:
        insert_metric_definition(unified_key=unified_key)

    print(f"✅ Real-time metrics ingested from {datacenter_name}.")
