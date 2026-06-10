# cloud_metrics/services/keyword_learning.py
from datetime import datetime
from cloud_metrics.utils.config import SessionLocal

def learn_keyword(raw_key: str, category: str, subcategory: str, short_key: str, confidence: float):
    from cloud_metrics.services.mapping_registry_service import create_mapping
    from cloud_metrics.models.cim_mapping import CimMapping
    from cloud_metrics.models.metric_definition import MetricDefinition
    
    raw = raw_key.strip()
    unified_key = f"gd.{category.lower()}.{subcategory.lower()}.{short_key.lower()}"
    
    with SessionLocal() as session:
        # Check if metric definition exists
        metric_def = session.query(MetricDefinition).filter_by(unified_key=unified_key).first()
        if not metric_def:
            metric_def = MetricDefinition(unified_key=unified_key, status="active")
            session.add(metric_def)
            session.commit()
            session.refresh(metric_def)
            
        existing = session.query(CimMapping).filter_by(source_key=raw).first()
        if existing:
            existing.cim_metric_id = metric_def.id
            existing.confidence = float(confidence)
            existing.updated_at = datetime.utcnow()
        else:
            create_mapping(
                source_key=raw,
                unified_key=unified_key,
                relation_type="exactMatch",
                confidence=float(confidence),
                rationale="Auto-learned keyword mapping"
            )
        session.commit()
