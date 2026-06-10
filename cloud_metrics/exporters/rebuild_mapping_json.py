# cloud_metrics/exporters/rebuild_mapping_json.py

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any

from cloud_metrics.utils.config import SessionLocal
from cloud_metrics.utils.unified_key import to_gd

DEFAULT_RELATIVE_PATH = Path("cloud_metrics") / "data" / "metric_mapping.json"

def _default_output_path() -> Path:
    env_path = (
        os.getenv("METRIC_MAPPING_JSON_PATH")
        or os.getenv("CLOUD_METRICS_MAPPING_PATH")
        or ""
    ).strip()

    if env_path:
        p = Path(env_path)
    else:
        p = DEFAULT_RELATIVE_PATH

    p.parent.mkdir(parents=True, exist_ok=True)
    return p

def rebuild_mapping(output_path: str | os.PathLike | None = None) -> str:
    path = Path(output_path) if output_path else _default_output_path()
    with SessionLocal() as s:
        from cloud_metrics.models.cim_mapping import CimMapping
        
        # Query all approved mappings
        mappings = s.query(CimMapping).filter(CimMapping.status == "approved").all()
        
        data = {}
        for m in mappings:
            raw = m.source_key
            uni = to_gd(m.cim_metric.unified_key)
            ts = (m.updated_at or datetime.utcnow()).replace(tzinfo=timezone.utc).isoformat()
            data[raw] = {"unified_key": uni, "last_seen": ts}

    payload = {
        "generated_at": datetime.utcnow().replace(tzinfo=timezone.utc).isoformat(),
        "count": len(data),
        "mappings": data,
    }

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    return str(path.resolve())
