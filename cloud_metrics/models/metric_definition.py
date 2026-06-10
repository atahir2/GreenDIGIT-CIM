# cloud_metrics/models/metric_definition.py

import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import Column, Integer, String, Text, JSON, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from cloud_metrics.models.db_models import Base

class MetricDefinition(Base):
    __tablename__ = "metric_definitions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    unified_key = Column(String(255), nullable=False, unique=True)
    
    # New registry fields
    label = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    domain = Column(String(64), nullable=True) # energy, performance, network, storage, environment
    quantity_kind_id = Column(Integer, ForeignKey("quantity_kinds.id"), nullable=True)
    canonical_unit_id = Column(Integer, ForeignKey("units.id"), nullable=True)
    metric_type = Column(String(64), nullable=True) # observed, calculated, derived, aggregated, reported
    status = Column(String(64), nullable=False, server_default="draft") # draft, active, deprecated, retired
    version = Column(Integer, nullable=False, server_default="1")

    tags = Column(JSON, nullable=True)
    sources = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    quantity_kind = relationship("cloud_metrics.models.unit.QuantityKind", foreign_keys=[quantity_kind_id])
    canonical_unit = relationship("cloud_metrics.models.unit.Unit", foreign_keys=[canonical_unit_id])

    # Many-to-many via the link table; view-only keeps writes in your service layer
    standards = relationship("cloud_metrics.models.standard_models.Standard",
        secondary="metric_standard_map",
        primaryjoin="MetricDefinition.id==metric_standard_map.c.metric_definition_id",
        secondaryjoin="cloud_metrics.models.standard_models.Standard.id==metric_standard_map.c.standard_id",
        viewonly=True,
    )