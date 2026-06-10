from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import pytest

from cloud_metrics.models.db_models import Base
import cloud_metrics.services.sql_service as sql_service

@pytest.fixture(autouse=True)
def use_sqlite_memory(monkeypatch):
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    monkeypatch.setattr(sql_service, "SessionLocal", Session)
    yield

def test_insert_and_query():
    now = datetime.utcnow()
    data = [("cpu_usage", 10.5, {"region":"us"}, now, "aws")]
    sql_service.insert_metrics(data)

    start = now - timedelta(minutes=1)
    end = now + timedelta(minutes=1)
    results = sql_service.query_sql_metrics("cpu_usage", start, end)
    assert len(results) == 1
    rec = results[0]
    assert rec.measurement == "cpu_usage"
    assert rec.value == 10.5
    assert rec.tags == {"region":"us"}
    assert rec.source == "aws"
