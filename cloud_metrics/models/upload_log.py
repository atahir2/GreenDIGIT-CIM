# cloud_metrics/models/upload_log.py

import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from cloud_metrics.models.db_models import Base

class FileUploadLog(Base):
    __tablename__ = "file_upload_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String(512), nullable=False)
    datacenter_id = Column(Integer, ForeignKey("datacenters.id", ondelete="CASCADE"), nullable=False)
    uploaded_by = Column(String(255), nullable=True)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())

    # Back‐reference to Datacenter
    datacenter = relationship("Datacenter", back_populates="upload_logs")
