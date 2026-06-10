# cloud_metrics/services/influx_service.py
from pathlib import Path
import sys

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from datetime import datetime
from typing import Any, Iterable, Mapping, Optional, Tuple
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from cloud_metrics.utils.config import get_influx_settings

_client: Optional[InfluxDBClient] = None
_write_api = None


def _ensure_client():
    """
    Lazily initialize the Influx client and write API.
    Cast URL to str to satisfy the client (fixes 'url attribute is not str instance').
    """
    global _client, _write_api
    if _client is None or _write_api is None:
        s = get_influx_settings()
        url = str(s.INFLUX_URL)  # ensure plain string
        _client = InfluxDBClient(url=url, token=s.INFLUX_TOKEN, org=s.INFLUX_ORG)
        _write_api = _client.write_api(write_options=SYNCHRONOUS)
    return _client, _write_api


def _to_points(measurements: Iterable[Tuple[str, float, Optional[Mapping[str, Any]], datetime]]):
    points = []
    for name, val, tags, ts in measurements:
        p = Point(str(name)).field("value", float(val)).time(ts, WritePrecision.NS)
        for k, v in (tags or {}).items():
            p.tag(str(k), str(v))
        points.append(p)
    return points


def write_metrics(measurements: Iterable[Tuple[str, float, Optional[Mapping[str, Any]], datetime]]) -> None:
    _, write_api = _ensure_client()
    s = get_influx_settings()
    points = _to_points(measurements)
    write_api.write(bucket=s.INFLUX_BUCKET, record=points)


def write_mapped_metrics(data, timestamp: Optional[datetime] = None) -> None:
    """
    Backwards-compatible wrapper that accepts:
      1) dict + timestamp:         write_mapped_metrics({'cpu': 0.5, ...}, ts)
      2) iterable of 3-tuples:     [(name, value, ts), ...]
      3) iterable of 4-tuples:     [(name, value, tags, ts), ...]
    """
    # Case 1: dict + timestamp
    if isinstance(data, dict):
        ts = timestamp or datetime.utcnow()
        measurements = [(k, float(v), {}, ts) for k, v in data.items()]
        return write_metrics(measurements)

    # Case 2/3: iterable of tuples (3 or 4)
    measurements = []
    for item in data:
        if not isinstance(item, tuple):
            raise TypeError("write_mapped_metrics expects a dict or an iterable of tuples")
        if len(item) == 4:
            measurements.append(item)  # (name, value, tags, ts)
        elif len(item) == 3:
            name, val, ts = item
            measurements.append((name, val, {}, ts))  # promote to 4-tuple
        else:
            raise ValueError(f"Unsupported measurement tuple length: {len(item)}. Expected 3 or 4.")
    write_metrics(measurements)


def query_metrics(
    measurement: str,
    start: str = "-1h",
    stop: Optional[str] = None,
    **filters,
) -> list[dict]:
    client, _ = _ensure_client()
    s = get_influx_settings()

    flux = f'from(bucket: "{s.INFLUX_BUCKET}") |> range(start: {start}'
    if stop:
        flux += f', stop: {stop}'
    flux += f') |> filter(fn: (r) => r._measurement == "{measurement}")'
    for tag, val in filters.items():
        flux += f' |> filter(fn: (r) => r["{tag}"] == "{val}")'

    df = client.query_api().query_data_frame(flux, org=s.INFLUX_ORG)
    return df.to_dict(orient="records")
