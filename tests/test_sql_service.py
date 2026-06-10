from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import pytest

from cloud_metrics.models.db_models import Base
from cloud_metrics.models.metric_sample import MetricSample
from cloud_metrics.services.insert_datacenter import get_or_create_datacenter_id
from cloud_metrics.services.insert_metric_sample import insert_metric_sample

@pytest.fixture(autouse=True)
def use_sqlite_memory(monkeypatch):
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    
    # Patch SessionLocal on both services that use it
    monkeypatch.setattr("cloud_metrics.services.insert_datacenter.SessionLocal", Session)
    monkeypatch.setattr("cloud_metrics.services.insert_metric_sample.SessionLocal", Session)
    
    # Provide the Session to the test function via yield if needed
    yield Session

def test_insert_and_query_sample(use_sqlite_memory):
    Session = use_sqlite_memory
    
    # Get or create a datacenter
    dc_id = get_or_create_datacenter_id("test_dc")
    assert dc_id is not None
    
    # Insert metric sample
    now = datetime.utcnow()
    insert_metric_sample(
        datacenter_id=dc_id,
        unified_key="gd.performance.cpu.utilization",
        raw_key="CPUUtilization",
        value=85.5,
        unit="%",
        tags={"region": "us-east-1"},
        source_file="test.json",
        captured_at=now,
        clf_confidence=1.0,
        clf_rationale="test mapping",
        domain="cloud"
    )
    
    # Query database directly using the session to assert values
    with Session() as s:
        samples = s.query(MetricSample).all()
        assert len(samples) == 1
        sample = samples[0]
        assert sample.datacenter_id == dc_id
        assert sample.unified_key == "gd.performance.cpu.utilization"
        assert sample.raw_key == "CPUUtilization"
        assert sample.value == 85.5
        assert sample.unit == "%"
        assert sample.tags == {"region": "us-east-1"}
        assert sample.source_file == "test.json"
        assert sample.clf_confidence == 1.0
        assert sample.clf_rationale == "test mapping"
        assert sample.domain == "cloud"

