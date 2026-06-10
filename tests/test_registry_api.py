# tests/test_registry_api.py

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import pytest

from cloud_metrics.models.db_models import Base
from cloud_metrics.models.unit import QuantityKind, Unit
from cloud_metrics.models.source import Source
from cloud_metrics.models.asset import Asset
from cloud_metrics.models.metric_definition import MetricDefinition
from cloud_metrics.models.cim_mapping import CimMapping
from cloud_metrics.models.provenance import ProvenanceRecord
from cloud_metrics.main import app

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_test_db(monkeypatch):
    from sqlalchemy.pool import StaticPool
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    
    # Patch SessionLocal across all modules
    modules_to_patch = [
        "cloud_metrics.api.registry_api",
        "cloud_metrics.utils.mapping_sync",
        "cloud_metrics.services.unit_registry_service",
        "cloud_metrics.services.standards_registry",
        "cloud_metrics.services.registry_service",
        "cloud_metrics.services.provenance_registry_service",
        "cloud_metrics.services.namespace_generator",
        "cloud_metrics.services.mapping_registry_service",
        "cloud_metrics.services.keyword_learning",
        "cloud_metrics.services.insert_metric_sample",
        "cloud_metrics.services.insert_metric_definition",
        "cloud_metrics.services.insert_mapped_metric",
        "cloud_metrics.services.insert_file_upload_log",
        "cloud_metrics.services.insert_datacenter",
        "cloud_metrics.registry.namespace_registry",
        "cloud_metrics.registry.mapping_registry",
        "cloud_metrics.ingestion.automated_mapper",
        "cloud_metrics.services.rule_registry_service",
    ]
    for mod_path in modules_to_patch:
        try:
            __import__(mod_path)
            monkeypatch.setattr(f"{mod_path}.SessionLocal", Session)
        except (ImportError, AttributeError):
            pass
            
    # Seed base elements
    with Session() as s:
        # QuantityKind & Unit
        qk = QuantityKind(name="Energy", description="Energy kind")
        s.add(qk)
        s.commit()
        
        u = Unit(symbol="kWh", name="kilowatt-hour", quantity_kind_id=qk.id, si_base=False, conversion_factor=1.0)
        s.add(u)
        
        # MetricDefinition
        m = MetricDefinition(
            unified_key="gd.energy.consumption.total",
            label="Total Energy Consumption",
            canonical_unit_id=u.id,
            quantity_kind_id=qk.id,
            status="active"
        )
        s.add(m)
        
        # Source
        src = Source(name="file_upload", type="file")
        s.add(src)
        
        # Asset
        ast = Asset(name="datacenter_A", type="datacenter", status="active")
        s.add(ast)
        
        s.commit()
        
    yield Session

def test_get_quantity_kinds():
    response = client.get("/api/v1/registry/quantity-kinds")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Energy"

def test_get_units():
    response = client.get("/api/v1/registry/units")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["symbol"] == "kWh"

def test_get_metrics():
    response = client.get("/api/v1/registry/metrics")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["unified_key"] == "gd.energy.consumption.total"

def test_get_sources():
    response = client.get("/api/v1/registry/sources")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "file_upload"

def test_get_assets():
    response = client.get("/api/v1/registry/assets")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "datacenter_A"

def test_mapping_proposal_and_approval():
    # Propose mapping
    payload = {
        "source_key": "Energy_kWh_Raw",
        "unified_key": "gd.energy.consumption.total",
        "relation_type": "exactMatch",
        "confidence": 0.95,
        "rationale": "Direct match in telemetry"
    }
    response = client.post("/api/v1/registry/mappings", json=payload)
    assert response.status_code == 200
    mapping = response.json()
    assert mapping["status"] == "proposed"
    assert mapping["source_key"] == "Energy_kWh_Raw"
    
    mapping_id = mapping["id"]
    
    # Approve mapping
    response = client.post(f"/api/v1/registry/mappings/{mapping_id}/approve")
    assert response.status_code == 200
    approved = response.json()
    assert approved["status"] == "approved"
    
    # Verify resolve mapping works now
    from cloud_metrics.services.mapping_registry_service import resolve_mapping
    res = resolve_mapping("Energy_kWh_Raw")
    assert res is not None
    assert res.cim_metric.unified_key == "gd.energy.consumption.total"

def test_get_provenance():
    # Create a provenance record
    from cloud_metrics.services.provenance_registry_service import record_activity
    record_activity(
        entity_type="metric_sample",
        entity_id=10,
        activity="ingestion",
        agent="test_agent",
        inputs={"val": 10},
        outputs={"val": 10},
        method="test",
        confidence=1.0
    )
    
    response = client.get("/api/v1/registry/provenance")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["agent"] == "test_agent"
