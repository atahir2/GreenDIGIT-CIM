from fastapi.testclient import TestClient
import pytest

@pytest.fixture
def client():
    from cloud_metrics.main import app
    return TestClient(app)

def test_ingest_aws(monkeypatch, client):
    called = {}
    monkeypatch.setattr(
        "cloud_metrics.api.metrics.ingest_aws_metrics",
        lambda: called.setdefault("aws", True),
    )
    res = client.get("/metrics/aws")
    assert res.status_code == 200
    assert res.json() == {"status": "aws metrics ingested"}
    assert called.get("aws")

def test_ingest_gcp(monkeypatch, client):
    called = {}
    monkeypatch.setattr(
        "cloud_metrics.api.metrics.ingest_gcp_metrics",
        lambda: called.setdefault("gcp", True),
    )
    res = client.get("/metrics/gcp")
    assert res.status_code == 200
    assert res.json() == {"status": "gcp metrics ingested"}
    assert called.get("gcp")

def test_query_endpoint(monkeypatch, client):
    sample = [{"_time": "2025-08-01T00:00:00Z", "_value": 1.23, "region":"us"}]
    monkeypatch.setattr(
        "cloud_metrics.api.query.query_metrics",
        lambda **kw: sample,
    )
    res = client.get("/query?measurement=cpu_usage")
    assert res.status_code == 200
    assert res.json() == sample

def test_query_bad(monkeypatch, client):
    def boom(**kw):
        raise RuntimeError("fail")
    monkeypatch.setattr(
        "cloud_metrics.api.query.query_metrics", boom
    )
    res = client.get("/query?measurement=cpu_usage")
    assert res.status_code == 500
    assert "Query failed" in res.json()["detail"]
