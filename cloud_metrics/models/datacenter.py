# cloud_metrics/models/datacenter.py

import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import Column, Integer, String, DateTime, func
from sqlalchemy.orm import relationship
from cloud_metrics.models.db_models import Base

class Datacenter(Base):
    __tablename__ = "datacenters"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, unique=True)
    location = Column(String(255), nullable=True)
    provider = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationship to upload logs
    upload_logs = relationship("FileUploadLog", back_populates="datacenter", cascade="all, delete-orphan",)
