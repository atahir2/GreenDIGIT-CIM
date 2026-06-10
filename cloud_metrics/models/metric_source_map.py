# cloud_metrics/models/metric_source_map.py

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint, func
from cloud_metrics.models.db_models import Base

class MetricSourceMap(Base):
    """
    Per-datacenter mapping of raw_key -> unified_key (audit of what we learned).
    """
    __tablename__ = "metric_source_map"
    __table_args__ = (
        UniqueConstraint("datacenter_id", "raw_key", name="uq_dc_rawkey"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    datacenter_id = Column(Integer, ForeignKey("datacenters.id"), nullable=False)
    raw_key = Column(String(255), nullable=False)
    unified_key = Column(String(255), nullable=False)
    first_seen = Column(DateTime(timezone=True), server_default=func.now())
    last_seen = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
