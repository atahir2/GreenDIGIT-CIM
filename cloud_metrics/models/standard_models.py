# cloud_metrics/models/standard_models.py

from __future__ import annotations

from sqlalchemy import Column, Integer, Text, Float, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
# If Base is elsewhere, adjust the import accordingly.
from cloud_metrics.models.db_models import Base


class Standard(Base):
    __tablename__ = "standards"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True)
    code = Column(Text, unique=True, nullable=False)   # e.g. 'TGG-PUE', 'TGG-WUE', 'GHG', 'ISO-50001'
    name = Column(Text, nullable=False)
    url = Column(Text)
    description = Column(Text)

    # reverse link for MetricStandardMap
    metric_links = relationship("MetricStandardMap", back_populates="standard", cascade="all, delete-orphan")

    # reverse side for Category.standard
    # categories = relationship("Category", back_populates="standard")

class MetricStandardMap(Base):
    __tablename__ = "metric_standard_map"
    __table_args__ = (
        UniqueConstraint("metric_definition_id", "standard_id", name="uq_metric_standard"),
        {"extend_existing": True},
    )
    id = Column(Integer, primary_key=True)
    metric_definition_id = Column(Integer, ForeignKey("metric_definitions.id", ondelete="CASCADE"), nullable=False)
    standard_id = Column(Integer, ForeignKey("standards.id", ondelete="CASCADE"), nullable=False)
    standard_metric_code = Column(Text)   # optional: e.g. 'PUE', 'WUE', 'CFP'
    confidence = Column(Float)            # 0..1
    rationale = Column(Text)

    # forward link to Standard
    standard = relationship("Standard", back_populates="metric_links")

