# cloud_metrics/models/metric_sample.py

from sqlalchemy import Column, Numeric, Text, Integer, String, Float, DateTime, ForeignKey, JSON, func
from cloud_metrics.models.db_models import Base

class MetricSample(Base):
    __tablename__ = "metric_samples"

    id = Column(Integer, primary_key=True, autoincrement=True)
    datacenter_id = Column(Integer, ForeignKey("datacenters.id"), nullable=False, index=True)
    unified_key = Column(String(255), nullable=False, index=True)
    raw_key = Column(String(255), nullable=False)

    value = Column(Float, nullable=False)
    unit = Column(String(64), nullable=True)

    tags = Column(JSON, nullable=False, server_default='{}')           # optional extra tags for this sample

    source_file = Column(String(512), nullable=True)

    captured_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    ri_id = Column(String(128), nullable=True)
    node_id = Column(String(128), nullable=True)
    vm_id = Column(String(128), nullable=True)
    host = Column(String(256), nullable=True)
    site_id = Column(String(256), nullable=True)

    clf_confidence = Column(Float, nullable=True)
    clf_rationale = Column(Text, nullable=True)

    domain = Column(Text, nullable=True)  # 'cloud' | 'grid' | 'network' | ...
    extra_meta = Column(JSON, nullable=False, server_default='{}')