# cloud_metrics/api/registry_api.py

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

from cloud_metrics.utils.config import SessionLocal
from cloud_metrics.models.metric_definition import MetricDefinition
from cloud_metrics.models.unit import Unit, QuantityKind
from cloud_metrics.models.source import Source
from cloud_metrics.models.asset import Asset
from cloud_metrics.models.cim_mapping import CimMapping
from cloud_metrics.models.provenance import ProvenanceRecord
from cloud_metrics.services.mapping_registry_service import approve_mapping, create_mapping

router = APIRouter()

# --- Dependency ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# --- Pydantic Schemas ---

class QuantityKindCreate(BaseModel):
    name: str
    description: Optional[str] = None

class QuantityKindOut(BaseModel):
    id: int
    name: str
    description: Optional[str] = None

    class Config:
        from_attributes = True

class UnitCreate(BaseModel):
    symbol: str
    name: str
    quantity_kind_id: int
    conversion_factor: float
    canonical_unit_id: Optional[int] = None
    si_base: bool = False

class UnitOut(BaseModel):
    id: int
    symbol: str
    name: str
    quantity_kind_id: int
    conversion_factor: float
    canonical_unit_id: Optional[int] = None
    si_base: bool

    class Config:
        from_attributes = True

class MetricDefinitionCreate(BaseModel):
    unified_key: str
    label: Optional[str] = None
    description: Optional[str] = None
    domain: Optional[str] = None
    quantity_kind_id: Optional[int] = None
    canonical_unit_id: Optional[int] = None
    metric_type: Optional[str] = None
    status: str = "active"

class MetricDefinitionOut(BaseModel):
    id: int
    unified_key: str
    label: Optional[str] = None
    description: Optional[str] = None
    domain: Optional[str] = None
    quantity_kind_id: Optional[int] = None
    canonical_unit_id: Optional[int] = None
    metric_type: Optional[str] = None
    status: str
    version: int

    class Config:
        from_attributes = True

class SourceCreate(BaseModel):
    name: str
    type: str
    protocol: Optional[str] = None
    format: Optional[str] = None
    capabilities: Optional[Dict[str, Any]] = None

class SourceOut(BaseModel):
    id: int
    name: str
    type: str
    protocol: Optional[str] = None
    format: Optional[str] = None
    capabilities: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True

class AssetCreate(BaseModel):
    name: str
    type: str
    parent_id: Optional[int] = None
    status: str = "active"

class AssetOut(BaseModel):
    id: int
    name: str
    type: str
    parent_id: Optional[int] = None
    status: str

    class Config:
        from_attributes = True

class CimMappingCreate(BaseModel):
    source_key: str
    unified_key: str
    relation_type: str = "exactMatch"
    confidence: float = 1.0
    rationale: Optional[str] = None

class CimMappingOut(BaseModel):
    id: int
    source_key: str
    cim_metric_id: int
    relation_type: str
    confidence: float
    status: str
    rationale: Optional[str] = None
    origin: str

    class Config:
        from_attributes = True

class ProvenanceOut(BaseModel):
    id: int
    entity_type: str
    entity_id: Optional[int] = None
    activity: str
    agent: str
    created_at: datetime
    inputs: Optional[Dict[str, Any]] = None
    outputs: Optional[Dict[str, Any]] = None
    method: Optional[str] = None
    confidence: Optional[float] = None

    class Config:
        from_attributes = True


# --- Endpoints ---

# 1. Quantity Kinds & Units (Unit Registry)
@router.get("/quantity-kinds", response_model=List[QuantityKindOut])
def get_quantity_kinds(db=Depends(get_db)):
    return db.query(QuantityKind).all()

@router.post("/quantity-kinds", response_model=QuantityKindOut)
def create_quantity_kind(payload: QuantityKindCreate, db=Depends(get_db)):
    qk = QuantityKind(**payload.model_dump())
    db.add(qk)
    db.commit()
    db.refresh(qk)
    return qk

@router.get("/units", response_model=List[UnitOut])
def get_units(db=Depends(get_db)):
    return db.query(Unit).all()

@router.post("/units", response_model=UnitOut)
def create_unit(payload: UnitCreate, db=Depends(get_db)):
    unit = Unit(**payload.model_dump())
    db.add(unit)
    db.commit()
    db.refresh(unit)
    return unit


# 2. Metric Definitions (Metric Registry)
@router.get("/metrics", response_model=List[MetricDefinitionOut])
def get_metrics(db=Depends(get_db)):
    return db.query(MetricDefinition).all()

@router.post("/metrics", response_model=MetricDefinitionOut)
def create_metric_definition(payload: MetricDefinitionCreate, db=Depends(get_db)):
    # Check if already exists
    existing = db.query(MetricDefinition).filter_by(unified_key=payload.unified_key).first()
    if existing:
        raise HTTPException(status_code=400, detail="Metric definition already exists")
    mdef = MetricDefinition(**payload.model_dump())
    db.add(mdef)
    db.commit()
    db.refresh(mdef)
    return mdef


# 3. Source Registry
@router.get("/sources", response_model=List[SourceOut])
def get_sources(db=Depends(get_db)):
    return db.query(Source).all()

@router.post("/sources", response_model=SourceOut)
def create_source(payload: SourceCreate, db=Depends(get_db)):
    src = Source(**payload.model_dump())
    db.add(src)
    db.commit()
    db.refresh(src)
    return src


# 4. Asset Registry
@router.get("/assets", response_model=List[AssetOut])
def get_assets(db=Depends(get_db)):
    return db.query(Asset).all()

@router.post("/assets", response_model=AssetOut)
def create_asset(payload: AssetCreate, db=Depends(get_db)):
    asset = Asset(**payload.model_dump())
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


# 5. Mapping Registry
@router.get("/mappings", response_model=List[CimMappingOut])
def get_mappings(db=Depends(get_db)):
    return db.query(CimMapping).all()

@router.post("/mappings", response_model=CimMappingOut)
def propose_mapping(payload: CimMappingCreate, db=Depends(get_db)):
    # Validate the unified key exists
    metric = db.query(MetricDefinition).filter_by(unified_key=payload.unified_key).first()
    if not metric:
        raise HTTPException(status_code=404, detail=f"Unified key '{payload.unified_key}' not found in Metric Registry")
    
    mapping = create_mapping(
        source_key=payload.source_key,
        unified_key=payload.unified_key,
        relation_type=payload.relation_type,
        confidence=payload.confidence,
        rationale=payload.rationale
    )
    return mapping

@router.post("/mappings/{mapping_id}/approve", response_model=CimMappingOut)
def approve_proposed_mapping(mapping_id: int, approved_by: str = "admin", db=Depends(get_db)):
    try:
        mapping = approve_mapping(mapping_id, approved_by=approved_by)
        if not mapping:
            raise HTTPException(status_code=404, detail="Mapping not found")
        return mapping
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# 6. Provenance Registry
@router.get("/provenance", response_model=List[ProvenanceOut])
def get_provenance(db=Depends(get_db)):
    return db.query(ProvenanceRecord).order_by(ProvenanceRecord.created_at.desc()).limit(100).all()
