# cloud_metrics/services/unit_registry_service.py

from typing import Optional
from cloud_metrics.utils.config import SessionLocal
from cloud_metrics.models.unit import Unit, QuantityKind

def get_unit_by_symbol(symbol: str) -> Optional[Unit]:
    with SessionLocal() as session:
        return session.query(Unit).filter_by(symbol=symbol).first()

def get_quantity_kind_by_name(name: str) -> Optional[QuantityKind]:
    with SessionLocal() as session:
        return session.query(QuantityKind).filter_by(name=name).first()

def get_canonical_unit(quantity_kind_name: str) -> Optional[Unit]:
    with SessionLocal() as session:
        qk = session.query(QuantityKind).filter_by(name=quantity_kind_name).first()
        if not qk:
            return None
        # Find unit where canonical_unit_id is NULL and quantity_kind_id matches
        return session.query(Unit).filter_by(
            quantity_kind_id=qk.id,
            canonical_unit_id=None
        ).first()

def validate_unit_for_quantity(unit_symbol: str, quantity_kind_name: str) -> bool:
    with SessionLocal() as session:
        qk = session.query(QuantityKind).filter_by(name=quantity_kind_name).first()
        if not qk:
            return False
        unit = session.query(Unit).filter_by(symbol=unit_symbol, quantity_kind_id=qk.id).first()
        return unit is not None

def convert_value(value: float, from_unit_symbol: str, to_unit_symbol: str) -> float:
    if from_unit_symbol == to_unit_symbol:
        return value
        
    with SessionLocal() as session:
        from_unit = session.query(Unit).filter_by(symbol=from_unit_symbol).first()
        to_unit = session.query(Unit).filter_by(symbol=to_unit_symbol).first()
        
        if not from_unit or not to_unit:
            raise ValueError(f"Unit symbols not found: '{from_unit_symbol}' or '{to_unit_symbol}'")
            
        if from_unit.quantity_kind_id != to_unit.quantity_kind_id:
            qk_from = session.query(QuantityKind).get(from_unit.quantity_kind_id)
            qk_to = session.query(QuantityKind).get(to_unit.quantity_kind_id)
            raise ValueError(
                f"Cannot convert between different quantity kinds: "
                f"'{qk_from.name}' ({from_unit_symbol}) to '{qk_to.name}' ({to_unit_symbol})"
            )
            
        # 1. Convert value to canonical unit value
        # formula: canon_val = value * factor + offset
        canon_val = value * from_unit.conversion_factor + from_unit.conversion_offset
        
        # 2. Convert canonical unit value to target unit value
        # formula: target_val = (canon_val - offset) / factor
        target_val = (canon_val - to_unit.conversion_offset) / to_unit.conversion_factor
        
        return target_val
