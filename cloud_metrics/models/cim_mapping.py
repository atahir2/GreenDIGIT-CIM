# cloud_metrics/models/cim_mapping.py

from sqlalchemy import Column, Integer, String, Float, Text, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from cloud_metrics.models.db_models import Base

class CimMapping(Base):
    __tablename__ = "cim_mappings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_key = Column(String(255), nullable=False, index=True)
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=True, index=True)
    cim_metric_id = Column(Integer, ForeignKey("metric_definitions.id"), nullable=False, index=True)
    standard_id = Column(Integer, ForeignKey("standards.id"), nullable=True, index=True)
    
    # exactMatch, closeMatch, broadMatch, narrowMatch, inputToKPI, derivedFrom, contextualMatch, extensionMetric, noMatch, underReview
    relation_type = Column(String(64), nullable=False, default="underReview")
    confidence = Column(Float, nullable=False, default=1.0)
    rationale = Column(Text, nullable=True)
    approved_by = Column(String(128), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    
    # proposed, approved, rejected, deprecated
    status = Column(String(64), nullable=False, default="proposed")
    version = Column(Integer, nullable=False, default=1)
    
    # manual, auto-learned, seeded, imported
    origin = Column(String(64), nullable=False, default="manual")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    source = relationship("Source", lazy="joined")
    cim_metric = relationship("MetricDefinition", foreign_keys=[cim_metric_id], lazy="joined")
    standard = relationship("Standard", foreign_keys=[standard_id], lazy="joined")
