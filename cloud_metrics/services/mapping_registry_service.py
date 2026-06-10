# cloud_metrics/services/mapping_registry_service.py

from datetime import datetime
from typing import Optional, List
from sqlalchemy import func
from cloud_metrics.utils.config import SessionLocal
from cloud_metrics.models.cim_mapping import CimMapping
from cloud_metrics.models.metric_definition import MetricDefinition
from cloud_metrics.utils.unified_key import to_gd

def resolve_mapping(raw_key: str) -> Optional[CimMapping]:
    """
    Resolve a raw source key to its approved mapping in the registry.
    Performs a case-insensitive check first.
    """
    with SessionLocal() as session:
        # Check for approved mappings matching raw_key case-insensitively
        mapping = (
            session.query(CimMapping)
            .filter(
                func.lower(CimMapping.source_key) == raw_key.lower(),
                CimMapping.status == "approved"
            )
            .first()
        )
        return mapping

def create_mapping(
    *,
    source_key: str,
    unified_key: str,
    source_id: Optional[int] = None,
    relation_type: str = "underReview",
    confidence: float = 1.0,
    rationale: Optional[str] = None,
    origin: str = "manual"
) -> CimMapping:
    unified_key = to_gd(unified_key)
    with SessionLocal() as session:
        # Resolve target metric definition
        metric_def = session.query(MetricDefinition).filter_by(unified_key=unified_key).first()
        if not metric_def:
            metric_def = MetricDefinition(unified_key=unified_key, status="draft")
            session.add(metric_def)
            session.flush()

        # Check if proposed mapping already exists
        mapping = session.query(CimMapping).filter_by(
            source_key=source_key,
            cim_metric_id=metric_def.id
        ).first()

        if not mapping:
            mapping = CimMapping(
                source_key=source_key,
                source_id=source_id,
                cim_metric_id=metric_def.id,
                relation_type=relation_type,
                confidence=confidence,
                rationale=rationale,
                status="proposed",
                origin=origin
            )
            session.add(mapping)
            session.commit()
            session.refresh(mapping)
        return mapping

def approve_mapping(mapping_id: int, approved_by: str) -> Optional[CimMapping]:
    with SessionLocal() as session:
        mapping = session.query(CimMapping).get(mapping_id)
        if mapping:
            mapping.status = "approved"
            mapping.approved_by = approved_by
            mapping.approved_at = func.now()
            session.commit()
            session.refresh(mapping)
        return mapping

def reject_mapping(mapping_id: int) -> Optional[CimMapping]:
    with SessionLocal() as session:
        mapping = session.query(CimMapping).get(mapping_id)
        if mapping:
            mapping.status = "rejected"
            session.commit()
            session.refresh(mapping)
        return mapping

def auto_learn_mapping(
    raw_key: str,
    unified_key: str,
    confidence: float = 0.85,
    rationale: Optional[str] = None
) -> CimMapping:
    """
    Registry wrapper for self-improving auto-learned mappings.
    Creates a proposed mapping with auto-learned origin.
    """
    return create_mapping(
        source_key=raw_key,
        unified_key=unified_key,
        relation_type="closeMatch",
        confidence=confidence,
        rationale=rationale or "Auto-learned by ingestion pipeline",
        origin="auto-learned"
    )
