# cloud_metrics/models/metric_keyword.py

import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import Column, Integer, String, Float, DateTime, func
from cloud_metrics.models.db_models import Base

class MetricKeyword(Base):
    __tablename__ = "metric_keywords"

    id = Column(Integer, primary_key=True, autoincrement=True)
    keyword = Column(String(255), nullable=False, unique=True)
    category = Column(String(255), nullable=True)
    subcategory = Column(String(255), nullable=True)
    short_key = Column(String(255), nullable=True)
    source_key = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
