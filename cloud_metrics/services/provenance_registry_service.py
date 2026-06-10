# cloud_metrics/services/provenance_registry_service.py

from datetime import datetime
from typing import Optional, Dict, Any
from cloud_metrics.utils.config import SessionLocal
from cloud_metrics.models.provenance import ProvenanceRecord

def record_activity(
    *,
    entity_type: str,
    entity_id: Optional[int] = None,
    activity: str,
    agent: str,
    started_at: Optional[datetime] = None,
    ended_at: Optional[datetime] = None,
    inputs: Optional[Dict[str, Any]] = None,
    outputs: Optional[Dict[str, Any]] = None,
    method: Optional[str] = None,
    confidence: Optional[float] = None,
    prov_uri: Optional[str] = None
) -> ProvenanceRecord:
    """
    Log an activity provenance entry in the database.
    """
    with SessionLocal() as session:
        record = ProvenanceRecord(
            entity_type=entity_type,
            entity_id=entity_id,
            activity=activity,
            agent=agent,
            started_at=started_at,
            ended_at=ended_at,
            inputs=inputs or {},
            outputs=outputs or {},
            method=method,
            confidence=confidence,
            prov_uri=prov_uri
        )
        session.add(record)
        session.commit()
        session.refresh(record)
        return record
