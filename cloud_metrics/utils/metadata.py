# cloud_metrics/utils/metadata.py
from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, Tuple

@dataclass
class IngestMeta:
    datacenter: str
    ri_id: str | None = None
    node_id: str | None = None
    vm_id: str | None = None
    host: str | None = None
    site_id: str | None = None
    timestamp: datetime | None = None
    extra: Dict[str, Any] | None = None

def _first(doc: dict, *names: str) -> Any:
    for n in names:
        if n in doc: return doc[n]
        # case-insensitive fallback
    low = {k.lower(): v for k, v in doc.items()}
    for n in names:
        if n.lower() in low: return low[n.lower()]
    return None

def parse_partner_metadata(doc: dict, filename_stem: str) -> Tuple[IngestMeta, dict[str, float]]:
    if not isinstance(doc, dict):
        raise ValueError("Top-level document must be an object")

    meta = doc.get("metadata") or {}
    if not isinstance(meta, dict):
        raise ValueError("metadata must be an object")

    # datacenter (required)
    dc = _first(meta, "datacenter", "data_center", "dc", "dc_name")
    if not dc or not str(dc).strip():
        raise ValueError("metadata.datacenter is required")

    ri_id   = _first(meta, "ri_id", "ri")
    node_id = _first(meta, "node_id", "node")
    vm_id   = _first(meta, "vm_id", "vm")
    host    = _first(meta, "host", "hostname")

    site_id = _first(meta, "site_id")
    if not site_id:
        parts = [x for x in [ri_id, node_id, vm_id] if x]
        site_id = ".".join(parts) if parts else None

    ts = _first(meta, "timestamp", "ts", "time")
    ts_parsed = None
    if ts:
        try:
            ts_parsed = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        except Exception:
            ts_parsed = None

    # capture extra keys (minus known ones)
    known = {"datacenter","data_center","dc","dc_name",
             "ri_id","ri","node_id","node","vm_id","vm",
             "host","hostname","site_id","timestamp","ts","time"}
    extra = {k: v for k, v in meta.items() if k not in known}

    # metrics
    metrics_obj = doc.get("metrics") or {}
    if not isinstance(metrics_obj, dict):
        raise ValueError("metrics must be an object")

    metrics: dict[str, float] = {}
    bad: list[str] = []
    for k, v in metrics_obj.items():
        try:
            metrics[str(k)] = float(v)
        except (TypeError, ValueError):
            bad.append(str(k))
    # optional: you can decide to raise on bad metrics
    # if bad: raise ValueError(f"Non-numeric metric values for: {', '.join(bad)}")

    return (
        IngestMeta(
            datacenter=str(dc).strip(),
            ri_id=str(ri_id).strip() if ri_id else None,
            node_id=str(node_id).strip() if node_id else None,
            vm_id=str(vm_id).strip() if vm_id else None,
            host=str(host).strip() if host else None,
            site_id=str(site_id).strip() if site_id else None,
            timestamp=ts_parsed,
            extra=extra or None,
        ),
        metrics
    )
