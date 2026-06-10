# cloud_metrics/models/provenance.py

from sqlalchemy import Column, Integer, String, Float, Text, JSON, DateTime, func
from cloud_metrics.models.db_models import Base

class ProvenanceRecord(Base):
    __tablename__ = "provenance_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    entity_type = Column(String(64), nullable=False) # metric_sample, cim_mapping, metric_definition
    entity_id = Column(Integer, nullable=True) # ID of affected entity
    
    # ingestion, classification, mapping, unit_conversion, aggregation, export, approval
    activity = Column(String(64), nullable=False)
    agent = Column(String(128), nullable=False) # system component or user ID
    
    started_at = Column(DateTime(timezone=True), nullable=True)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    
    inputs = Column(JSON, nullable=True, server_default='{}')
    outputs = Column(JSON, nullable=True, server_default='{}')
    
    method = Column(String(128), nullable=True) # algorithm or rule used
    confidence = Column(Float, nullable=True)
    prov_uri = Column(String(256), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
