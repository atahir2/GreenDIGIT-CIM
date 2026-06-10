# cloud_metrics/exporters/rebuild_mapping_json.py

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any
from sqlalchemy import func

from cloud_metrics.utils.config import SessionLocal
from cloud_metrics.utils.unified_key import to_gd

# Models are optional; we import lazily to allow partial installs
try:
    from cloud_metrics.models.metric_source_map import MetricSourceMap
except Exception:
    MetricSourceMap = None  # type: ignore

try:
    from cloud_metrics.models.metric_keyword import MetricKeyword
except Exception:
    MetricKeyword = None  # type: ignore

DEFAULT_RELATIVE_PATH = Path("cloud_metrics") / "data" / "metric_mapping.json"


def _default_output_path() -> Path:
    """
    Resolve output path from env or fall back to repo-local data file.
    Env vars checked (first win):
      - METRIC_MAPPING_JSON_PATH
      - CLOUD_METRICS_MAPPING_PATH
    """
    env_path = (
        os.getenv("METRIC_MAPPING_JSON_PATH")
        or os.getenv("CLOUD_METRICS_MAPPING_PATH")
        or ""
    ).strip()

    if env_path:
        p = Path(env_path)
    else:
        p = DEFAULT_RELATIVE_PATH

    # Ensure folder exists
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _load_from_metric_source_map(session) -> dict[str, dict[str, Any]]:
    """
    Build mapping from MetricSourceMap, preferring the most recent last_seen for duplicates.
    Structure: { raw_key: { "unified_key": str, "last_seen": iso8601 } }
    """
    if MetricSourceMap is None:
        return {}

    rows = (
        session.query(
            MetricSourceMap.raw_key,
            MetricSourceMap.unified_key,
            func.max(MetricSourceMap.last_seen).label("last_seen"),
        )
        .group_by(MetricSourceMap.raw_key, MetricSourceMap.unified_key)
        .all()
    )

    latest: dict[str, dict[str, Any]] = {}
    # choose the unified_key with the latest last_seen per raw_key
    for raw_key, unified_key, last_seen in rows:
        raw = (raw_key or "").strip()
        uni = to_gd(unified_key or "")
        ts = (last_seen or datetime.utcnow()).replace(tzinfo=timezone.utc).isoformat()

        prev = latest.get(raw)
        if prev is None or ts > prev.get("last_seen", ""):
            latest[raw] = {"unified_key": uni, "last_seen": ts}
    return latest


def _fallback_from_metric_keywords(session) -> dict[str, dict[str, Any]]:
    """
    If source_map is empty or missing, fallback to MetricKeyword:
    keyword -> (category, subcategory, short_key) => gd.category.subcategory.short_key
    """
    if MetricKeyword is None:
        return {}

    rows = session.query(
        MetricKeyword.keyword,
        MetricKeyword.category,
        MetricKeyword.subcategory,
        MetricKeyword.short_key,
        getattr(MetricKeyword, "updated_at", None),
    ).all()

    out: dict[str, dict[str, Any]] = {}
    for r in rows:
        keyword = (r[0] or "").strip().lower()
        cat = (r[1] or "").strip().lower()
        sub = (r[2] or "").strip().lower()
        short = (r[3] or "").strip().lower()
        ts = r[4]
        uni = to_gd(f"gd.{cat}.{sub}.{short}")
        out[keyword] = {
            "unified_key": uni,
            "last_seen": (ts.replace(tzinfo=timezone.utc).isoformat() if ts else None),
        }
    return out


def rebuild_mapping(output_path: str | os.PathLike | None = None) -> str:
    """
    Rebuild mapping JSON from DB and write to disk.
    Returns the absolute file path written.
    JSON shape:
    {
      "generated_at": "...",
      "count": N,
      "mappings": {
        "<raw_key>": { "unified_key": "gd.x.y.z", "last_seen": "..." }
      }
    }
    """
    path = Path(output_path) if output_path else _default_output_path()
    with SessionLocal() as s:
        data = _load_from_metric_source_map(s)
        if not data:
            # fallback to keyword registry
            data = _fallback_from_metric_keywords(s)

    payload = {
        "generated_at": datetime.utcnow().replace(tzinfo=timezone.utc).iso8601()
        if hasattr(datetime.utcnow(), "iso8601")
        else datetime.utcnow().replace(tzinfo=timezone.utc).isoformat(),
        "count": len(data),
        "mappings": data,
    }

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    return str(path.resolve())
