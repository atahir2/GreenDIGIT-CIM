# cloud_metrics/classifiers/mapping_registry.py

from typing import Optional, Dict, Any, List
from datetime import datetime
from sqlalchemy import func
from cloud_metrics.utils.config import SessionLocal
from cloud_metrics.models.metric_keyword import MetricKeyword
from cloud_metrics.models.metric_source_map import MetricSourceMap
from cloud_metrics.services.insert_mapped_metric import insert_mapped_metric
from cloud_metrics.utils.mapping_sync import sync_metric_mapping

def upsert_keyword(raw_key: str, category: str, subcategory: str, short_key: str) -> None:
    raw = (raw_key or "").strip().lower()
    with SessionLocal() as s:
        mk = (s.query(MetricKeyword)
              .filter((MetricKeyword.keyword == raw) | (MetricKeyword.source_key == raw))
              .first())
        if mk:
            mk.category = category
            mk.subcategory = subcategory
            mk.short_key = short_key
            mk.updated_at = datetime.utcnow() if hasattr(mk, "updated_at") else mk.updated_at
        else:
            s.add(MetricKeyword(
                keyword=raw,
                source_key=raw,
                category=category,
                subcategory=subcategory,
                short_key=short_key,
            ))
        s.commit()

def register_mapping(
    *,
    datacenter_id: int,
    raw_key: str,
    unified_key: str,
    origin: str,
    value: float,
    unit: Optional[str],
    tags: Optional[List[str]] = None,
) -> None:
    """
    Side effects:
      - ensure metric_definitions has unified_key with source=origin
      - update metric_source_map(raw→unified, per-DC)
      - update metric_mapping.json (raw→unified)
      - (keyword learning is handled in ingestion based on confidence)
    """
    insert_mapped_metric(unified_key=unified_key, source_keys=[origin], tags=tags or [])
    sync_metric_mapping(unified_key=unified_key, source_key=raw_key)

    # update per-DC raw→unified dictionary timestamps
    with SessionLocal() as s:
        msm = (s.query(MetricSourceMap)
               .filter(MetricSourceMap.datacenter_id == datacenter_id,
                       MetricSourceMap.raw_key == raw_key)
               .first())
        if msm:
            msm.unified_key = unified_key
            msm.last_seen = func.now()
        else:
            s.add(MetricSourceMap(
                datacenter_id=datacenter_id,
                raw_key=raw_key,
                unified_key=unified_key,
            ))
        s.commit()
