# cloud_metrics/models/metric_definition.py

import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import Column, Integer, String, JSON, DateTime, func
from sqlalchemy.orm import relationship
from cloud_metrics.models.db_models import Base

class MetricDefinition(Base):
    __tablename__ = "metric_definitions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    unified_key = Column(String(255), nullable=False, unique=True)
    tags = Column(JSON, nullable=True)
    sources = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Many-to-many via the link table; view-only keeps writes in your service layer
    standards = relationship("cloud_metrics.models.standard_models.Standard",
        secondary="metric_standard_map",
        primaryjoin="MetricDefinition.id==metric_standard_map.c.metric_definition_id",
        secondaryjoin="cloud_metrics.models.standard_models.Standard.id==metric_standard_map.c.standard_id",
        viewonly=True,
    )