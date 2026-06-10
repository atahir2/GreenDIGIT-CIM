# cloud_metrics/models/metric_mapping.py
from sqlalchemy import Column, Integer, String, Float, DateTime, Enum, JSON, ForeignKey, func
from sqlalchemy.orm import relationship
import enum

from .db_models import Base

class MappingStatus(str, enum.Enum):
    PROPOSED = "PROPOSED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"

class MetricMapping(Base):
    """
    Canonical, approved raw->unified mapping (current version).
    """
    __tablename__ = "metric_mappings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    raw_key = Column(String(255), nullable=False, unique=True, index=True)
    unified_key = Column(String(255), nullable=False, index=True)
    version = Column(Integer, nullable=False, default=1)
    unit = Column(String(64), nullable=True)
    tags = Column(JSON, nullable=True)
    approved_at = Column(DateTime(timezone=True), server_default=func.now())

class MappingProposal(Base):
    """
    Proposed mapping with confidence and rationale; can be approved to become canonical.
    """
    __tablename__ = "mapping_proposals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    raw_key = Column(String(255), nullable=False, index=True)
    suggested_unified_key = Column(String(255), nullable=False)
    confidence = Column(Float, nullable=False)
    rationale = Column(String(1024), nullable=True)
    unit = Column(String(64), nullable=True)
    tags = Column(JSON, nullable=True)
    status = Column(Enum(MappingStatus), nullable=False, default=MappingStatus.PROPOSED)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class MappingEvent(Base):
    """
    Append-only audit trail of changes and approvals.
    """
    __tablename__ = "mapping_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    raw_key = Column(String(255), nullable=False, index=True)
    event = Column(String(64), nullable=False)  # PROPOSED, APPROVED, REJECTED, UPDATED
    payload = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
