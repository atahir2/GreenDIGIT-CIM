# tests/test_new_services.py

from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import pytest

from cloud_metrics.models.db_models import Base
from cloud_metrics.models.unit import QuantityKind, Unit
from cloud_metrics.models.source import Source
from cloud_metrics.models.metric_definition import MetricDefinition
from cloud_metrics.models.provenance import ProvenanceRecord
from cloud_metrics.models.cim_mapping import CimMapping
from cloud_metrics.models.standard_models import Standard

from cloud_metrics.services.unit_registry_service import convert_value, get_canonical_unit, validate_unit_for_quantity
from cloud_metrics.services.mapping_registry_service import create_mapping, resolve_mapping, approve_mapping, auto_learn_mapping
from cloud_metrics.services.rule_registry_service import validate_metric_sample
from cloud_metrics.services.provenance_registry_service import record_activity

@pytest.fixture(autouse=True)
def setup_test_db(monkeypatch):
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    
    # Patch SessionLocal across all modules to use SQLite in-memory Session
    modules_to_patch = [
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
    
    # Seed QuantityKinds and Units inside in-memory DB
    with Session() as s:
        energy_qk = QuantityKind(name="Energy", description="Energy kind")
        power_qk = QuantityKind(name="Power", description="Power kind")
        percent_qk = QuantityKind(name="Percentage", description="Percentage ratio")
        s.add_all([energy_qk, power_qk, percent_qk])
        s.commit()
        
        # Seed Units
        kwh = Unit(symbol="kWh", name="kilowatt-hour", quantity_kind_id=energy_qk.id, si_base=False, conversion_factor=1.0)
        wh = Unit(symbol="Wh", name="watt-hour", quantity_kind_id=energy_qk.id, si_base=False, canonical_unit_id=kwh.id, conversion_factor=0.001)
        w = Unit(symbol="W", name="watt", quantity_kind_id=power_qk.id, si_base=True, conversion_factor=1.0)
        pct = Unit(symbol="%", name="percent", quantity_kind_id=percent_qk.id, si_base=False, conversion_factor=1.0)
        s.add_all([kwh, wh, w, pct])
        
        # Seed Source
        src = Source(name="file_upload", type="file")
        s.add(src)
        
        # Seed Standard
        std = Standard(code="ISO", name="International Standards Organization")
        s.add(std)
        s.commit()
        
    yield Session

def test_unit_conversions():
    # Convert 1500 Wh to kWh (1.5 kWh)
    val = convert_value(1500.0, "Wh", "kWh")
    assert val == 1.5
    
    # Convert 2 kWh to Wh (2000 Wh)
    val = convert_value(2.0, "kWh", "Wh")
    assert val == 2000.0
    
    # Verify canonical unit resolution
    canon = get_canonical_unit("Energy")
    assert canon.symbol == "kWh"
    
    # Validate units
    assert validate_unit_for_quantity("Wh", "Energy") is True
    assert validate_unit_for_quantity("W", "Energy") is False

def test_mapping_lifecycle(setup_test_db):
    Session = setup_test_db
    
    # Create mapping
    mapping = create_mapping(
        source_key="power_consumption_w",
        unified_key="gd.energy.power.total",
        relation_type="closeMatch",
        confidence=0.9,
        rationale="manual mapping"
    )
    assert mapping.id is not None
    assert mapping.status == "proposed"
    
    # Resolve mapping should return None (not approved yet)
    assert resolve_mapping("power_consumption_w") is None
    
    # Approve mapping
    approve_mapping(mapping.id, "admin_user")
    
    # Resolve should now succeed
    res = resolve_mapping("power_consumption_w")
    assert res is not None
    assert res.cim_metric.unified_key == "gd.energy.power.total"
    
    # Auto-learn mapping
    learned = auto_learn_mapping("cpu_util", "gd.performance.cpu.utilization", confidence=0.88)
    assert learned.status == "proposed"
    assert learned.origin == "auto-learned"

def test_rule_validation(setup_test_db):
    # Rule 1: Starts with gd.
    errs = validate_metric_sample(unified_key="performance.cpu.utilization", value=50.0)
    assert any("Namespace error" in e for e in errs)
    
    # Rule 2: Numeric warning
    errs = validate_metric_sample(unified_key="gd.performance.cpu.utilization", value=50.0, unit=None)
    assert any("warning: metric" in e for e in errs)
    
    # Rule 3: Energy unit validation
    errs = validate_metric_sample(unified_key="gd.energy.consumption.total", value=5.0, unit="W")
    assert any("Unit conflict" in e for e in errs)
    
    # Rule 4: PUE range check
    errs = validate_metric_sample(unified_key="gd.energy.efficiency.pue", value=0.9, unit="%")
    assert any("PUE value 0.9 is less than 1.0" in e for e in errs)
    
    # Rule 6: Percentage range check
    errs = validate_metric_sample(unified_key="gd.performance.cpu.utilization", value=150.0, unit="%")
    assert any("percentage/utilization value 150.0" in e for e in errs)

def test_provenance_logging(setup_test_db):
    Session = setup_test_db
    
    rec = record_activity(
        entity_type="metric_sample",
        entity_id=99,
        activity="unit_conversion",
        agent="pipeline_unit_normalizer",
        inputs={"value": 1500, "unit": "Wh"},
        outputs={"value": 1.5, "unit": "kWh"},
        method="convert_value",
        confidence=1.0
    )
    assert rec.id is not None
    
    with Session() as s:
        log = s.query(ProvenanceRecord).get(rec.id)
        assert log.entity_type == "metric_sample"
        assert log.entity_id == 99
        assert log.activity == "unit_conversion"
        assert log.agent == "pipeline_unit_normalizer"
        assert log.inputs == {"value": 1500, "unit": "Wh"}
        assert log.outputs == {"value": 1.5, "unit": "kWh"}
        assert log.method == "convert_value"
        assert log.confidence == 1.0

def test_pipeline_ingestion(setup_test_db):
    Session = setup_test_db
    
    # 1. Setup MetricDefinition with kWh canonical unit
    with Session() as s:
        kwh_unit = s.query(Unit).filter_by(symbol="kWh").first()
        energy_qk = s.query(QuantityKind).filter_by(name="Energy").first()
        
        mdef = MetricDefinition(
            unified_key="gd.energy.consumption.total",
            canonical_unit_id=kwh_unit.id,
            quantity_kind_id=energy_qk.id,
            status="active"
        )
        s.add(mdef)
        s.commit()
        
    # 2. Call automated mapper pipeline
    from cloud_metrics.ingestion.automated_mapper import process_metric_sample
    from cloud_metrics.models.metric_sample import MetricSample
    
    # Ingest 2500 Wh from datacenter_A
    unified_key = process_metric_sample(
        raw_key="EnergyWh",
        value=2500.0,
        origin="datacenter_A"
    )
    assert unified_key == "gd.energy.consumption.total"
    
    # 3. Query sample to verify unit conversion (value should be 2.5 kWh, not 2500.0 Wh)
    with Session() as s:
        samples = s.query(MetricSample).all()
        assert len(samples) == 1
        sample = samples[0]
        assert sample.value == 2.5
        assert sample.unit == "kWh"
        
        # Verify provenance logs
        prov_records = s.query(ProvenanceRecord).all()
        assert len(prov_records) >= 2 # unit_conversion and ingestion
        
        activities = [p.activity for p in prov_records]
        assert "unit_conversion" in activities
        assert "ingestion" in activities

