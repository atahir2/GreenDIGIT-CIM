from datetime import datetime
import pytest

import cloud_metrics.services.influx_service as influx_service

def test_write_metrics_batches(monkeypatch):
    captured = {}
    class DummyWriteAPI:
        def write(self, bucket, record):
            captured["bucket"] = bucket
            captured["record"] = record

    dummy_write_api = DummyWriteAPI()
    monkeypatch.setattr(influx_service, "_ensure_client", lambda: (None, dummy_write_api))
    from cloud_metrics.utils.config import get_influx_settings

    now = datetime.utcnow()
    influx_service.write_metrics([
        ("cpu_usage", 5.5, {"region":"us-east"}, now),
    ])

    assert captured["bucket"] == get_influx_settings().INFLUX_BUCKET
    pts = captured["record"]
    assert len(pts) == 1
    line = pts[0].to_line_protocol()
    assert line.startswith("cpu_usage")
    assert "region=us-east" in line
    assert "value=5.5" in line
