# cloud_metrics/services/registry_service.py
from typing import Optional, Dict, Any
from sqlalchemy import inspect, select, update
from cloud_metrics.utils.config import SessionLocal

try:
    from cloud_metrics.models.metric_mapping import MetricMapping  # optional
except Exception:
    MetricMapping = None

def resolve_unified_key(raw_key: str) -> Optional[Dict[str, Any]]:
    """
    Return approved mapping for raw_key, or None
    If the registry table doesn't exist, safely return none.
    """
    if MetricMapping is None:
        return None

    with SessionLocal() as s:
        insp = inspect(s.bind)
        if "metric_mappings" not in insp.get_table_names():
            return None  # registry disabled

        mm = s.execute(select(MetricMapping).where(MetricMapping.raw_key == raw_key)).scalar_one_or_none()
        if not mm:
            return None
        return {
            "unified_key": mm.unified_key,
            "unit": mm.unit,
            "tags": mm.tags or {},
            "version": mm.version,
        }

