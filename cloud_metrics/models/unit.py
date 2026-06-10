# cloud_metrics/models/unit.py

from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from cloud_metrics.models.db_models import Base

class QuantityKind(Base):
    __tablename__ = "quantity_kinds"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(128), nullable=False, unique=True) # Energy, Power, Temperature, DataSize, DataRate, etc.
    description = Column(String(512), nullable=True)
    qudt_uri = Column(String(256), nullable=True)

    units = relationship("Unit", back_populates="quantity_kind", foreign_keys="[Unit.quantity_kind_id]")

class Unit(Base):
    __tablename__ = "units"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(64), nullable=False, unique=True) # Wh, kWh, W, kW, °C, GB, Mbps, etc.
    name = Column(String(128), nullable=False) # watt, kilowatt-hour, etc.
    quantity_kind_id = Column(Integer, ForeignKey("quantity_kinds.id"), nullable=False)
    si_base = Column(Boolean, nullable=False, default=False)
    
    canonical_unit_id = Column(Integer, ForeignKey("units.id"), nullable=True)
    conversion_factor = Column(Float, nullable=False, default=1.0) # factor * value
    conversion_offset = Column(Float, nullable=False, default=0.0) # value + offset
    qudt_uri = Column(String(256), nullable=True)
    saref_uri = Column(String(256), nullable=True)

    quantity_kind = relationship("QuantityKind", back_populates="units", foreign_keys=[quantity_kind_id])
    canonical_unit = relationship("Unit", remote_side=[id], foreign_keys=[canonical_unit_id])
