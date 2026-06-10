# cloud_metrics/services/insert_metric_sample.py

from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import func
from cloud_metrics.utils.config import SessionLocal
from cloud_metrics.models.metric_sample import MetricSample
from cloud_metrics.models.db_models import Base
from cloud_metrics.utils.unified_key import to_gd

def insert_metric_sample(
    *,
    datacenter_id: int,
    unified_key: str,
    raw_key: str,
    value: float,
    unit: Optional[str] = None,
    tags: Optional[Dict[str, Any]] = None,
    source_file: Optional[str] = None,
    captured_at: Optional[datetime] = None,
    ri_id: Optional[str] = None,
    node_id: Optional[str] = None,
    vm_id: Optional[str] = None,
    host: Optional[str] = None,
    site_id: Optional[str] = None,
    clf_confidence: Optional[float] = None,
    clf_rationale: Optional[str] = None,
    extra_meta: Optional[Dict[str, Any]] = None,
    domain: Optional[str] = None,
) -> int:
    with SessionLocal() as s:
        # Standardize extra_meta
        if extra_meta is None:
            extra_meta = {}
            
        sample = MetricSample(
            datacenter_id=datacenter_id,
            unified_key=to_gd(unified_key),
            raw_key=raw_key,
            value=value,
            unit=unit,
            tags=tags or {},
            source_file=source_file,
            captured_at=captured_at or datetime.utcnow(),
            ri_id=ri_id,
            node_id=node_id,
            vm_id=vm_id,
            host=host,
            site_id=site_id,
            clf_confidence=clf_confidence,
            clf_rationale=clf_rationale,
            extra_meta=extra_meta,
            domain=domain,
        )
        s.add(sample)
        s.commit()
        s.refresh(sample)
        return sample.id
