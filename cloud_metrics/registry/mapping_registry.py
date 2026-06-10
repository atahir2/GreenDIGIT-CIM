# cloud_metrics/registry/mapping_registry.py

from typing import Optional, Dict, Any, List
from datetime import datetime
from sqlalchemy import func
from cloud_metrics.utils.config import SessionLocal
from cloud_metrics.services.insert_mapped_metric import insert_mapped_metric
from cloud_metrics.utils.mapping_sync import sync_metric_mapping

def upsert_keyword(raw_key: str, category: str, subcategory: str, short_key: str) -> None:
    from cloud_metrics.services.mapping_registry_service import create_mapping, approve_mapping
    from cloud_metrics.models.metric_definition import MetricDefinition
    from cloud_metrics.models.cim_mapping import CimMapping
    raw = (raw_key or "").strip()
    unified_key = f"gd.{category.lower()}.{subcategory.lower()}.{short_key.lower()}"
    
    with SessionLocal() as session:
        metric_def = session.query(MetricDefinition).filter_by(unified_key=unified_key).first()
        if not metric_def:
            metric_def = MetricDefinition(unified_key=unified_key, status="active")
            session.add(metric_def)
            session.commit()
            session.refresh(metric_def)
            
        existing = session.query(CimMapping).filter_by(source_key=raw).first()
        if existing:
            existing.cim_metric_id = metric_def.id
            existing.status = "approved"
            existing.confidence = 1.0
            existing.updated_at = datetime.utcnow()
        else:
            mapping = create_mapping(
                source_key=raw,
                unified_key=unified_key,
                relation_type="exactMatch",
                confidence=1.0,
                rationale="Keyword learning upsert"
            )
            approve_mapping(mapping.id, approved_by="system")
        session.commit()

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
      - update CimMapping in db
      - update metric_mapping.json (raw→unified)
    """
    insert_mapped_metric(unified_key=unified_key, source_keys=[origin], tags=tags or [])
    sync_metric_mapping(unified_key=unified_key, source_key=raw_key)

    from cloud_metrics.services.mapping_registry_service import create_mapping, approve_mapping
    from cloud_metrics.models.metric_definition import MetricDefinition
    from cloud_metrics.models.cim_mapping import CimMapping

    with SessionLocal() as session:
        metric_def = session.query(MetricDefinition).filter_by(unified_key=unified_key).first()
        if not metric_def:
            metric_def = MetricDefinition(unified_key=unified_key, status="active")
            session.add(metric_def)
            session.commit()
            session.refresh(metric_def)
            
        existing = session.query(CimMapping).filter_by(source_key=raw).first()
        if existing:
            existing.cim_metric_id = metric_def.id
            existing.status = "approved"
            existing.updated_at = datetime.utcnow()
        else:
            mapping = create_mapping(
                source_key=raw,
                unified_key=unified_key,
                relation_type="exactMatch",
                confidence=1.0,
                rationale=f"Registered via telemetry pipeline for {origin}"
            )
            approve_mapping(mapping.id, approved_by="system")
        session.commit()
