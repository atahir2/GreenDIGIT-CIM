# cloud_metrics/models/asset.py

from sqlalchemy import Column, Integer, String, ForeignKey, JSON, DateTime, func
from sqlalchemy.orm import relationship
from cloud_metrics.models.db_models import Base

class Asset(Base):
    __tablename__ = "assets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(128), nullable=False)
    type = Column(String(64), nullable=False) # datacenter, cluster, rack, node, server, cpu, gpu, storage_system, network_device, vm, container, service, workflow, dataset, experiment
    parent_id = Column(Integer, ForeignKey("assets.id"), nullable=True)
    location = Column(String(256), nullable=True)
    provider = Column(String(128), nullable=True)
    specifications = Column(JSON, nullable=True, server_default='{}')
    lifecycle_stage_id = Column(Integer, nullable=True) # Will point to lifecycle_stages.id later
    status = Column(String(64), nullable=False, default="active") # active, inactive, decommissioned

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    parent = relationship("Asset", remote_side=[id], backref="children")
