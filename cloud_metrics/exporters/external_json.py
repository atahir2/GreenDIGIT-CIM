# cloud_metrics/exporters/external_json.py
from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Dict, Any, Optional

# Where to write partner JSON files. Override with EXTERNAL_OUTPUT_DIR env var.
_OUTPUT_DIR = os.path.normpath(os.getenv("EXTERNAL_OUTPUT_DIR", os.path.join(os.getcwd(), "output")))

def _iso(dt: Optional[datetime]) -> str:
    if not dt:
        return datetime.utcnow().isoformat()
    return dt.isoformat()

def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)

def unified_to_gd(unified_key: str) -> str:
    """
    Convert internal unified key (e.g., iso.performance.cpu.utilization)
    to external 'gd.category.subcategory.short_key'.

    Rules:
      - If the key has 4+ parts, drop the first part (standard) and prefix 'gd.'
      - If fewer parts or unknowns, still emit 'gd.' + best-effort remainder.
    """
    parts = (unified_key or "").split(".")
    if len(parts) >= 4:
        # [standard, category, subcategory, short, ...extras] -> keep the next three + short
        category, subcat, short = parts[1], parts[2], parts[3]
        rest = [category, subcat, short]
    elif len(parts) == 3:
        rest = parts  # already category.subcategory.short
    else:
        # unknown.* or malformed: try to keep last 3 tokens
        rest = parts[-3:] if len(parts) >= 3 else ["unknown", "unknown", "unknown"]
    return "gd." + ".".join(rest)

def build_metadata(
    *,
    ri_id: Optional[str] = None,
    node_id: Optional[str] = None,
    vm_id: Optional[str] = None,
    datacenter: Optional[str] = None,
    host: Optional[str] = None,
    timestamp: Optional[datetime] = None,
    site_id: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
    domain: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Build the metadata block for partner export.

    If site_id is not provided, we derive it from ri_id/node_id/vm_id with defaults:
    site_id = "{ri_id or datacenter}.default_node.default_vm"
    (and fill missing node/vm with 'default_node'/'default_vm')
    """

    # Compute site_id when absent
    if not site_id:
        # graceful defaults so it's always stable
        ri_part = (ri_id or datacenter or "site").strip() or "site"
        node_part = (node_id or "default_node").strip()
        vm_part = (vm_id or "default_vm").strip()
        site_id = ".".join([ri_part, node_part, vm_part])

    md = {
        "site_id": site_id,
        "ri_id": ri_id,
        "node_id": node_id,
        "vm_id": vm_id,
        "datacenter": datacenter,
        "host": host,
        "timestamp": _iso(timestamp),
    }

    # optional fields
    if extra:
        md["extra"] = extra
    if domain:
        md["domain"] = domain

    return md

def write_external_metrics_json(
    *,
    metadata: Dict[str, Any],
    metrics_unified_values: Dict[str, float],
    file_basename: str | None = None,
    out_dir: str = os.path.join("cloud_metrics", "data", "exports"),
) -> str:
    """
    Write partner JSON:
    {
      "metadata": {...},
      "metrics": { "gd.category.subcategory.short": value, ... }
    }
    Returns the path written.
    """
    os.makedirs(out_dir, exist_ok=True)
    # safe filename
    fname = f"{file_basename}_unified.json"
    out_path = os.path.join(out_dir, fname)

    payload = {
        "metadata": metadata,
        "metrics": metrics_unified_values or {},
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    return out_path

    # # Convert keys to gd.* form
    # gd_metrics: Dict[str, float] = {}
    # for uk, val in (metrics_unified_values or {}).items():
    #     try:
    #         gd_key = unified_to_gd(uk)
    #         gd_metrics[gd_key] = float(val)
    #     except Exception:
    #         # skip non-numeric
    #         continue
    #
    # payload = {"metadata": metadata, "metrics": gd_metrics}

    # # Name file: <site_id or datacenter>_<YYYYMMDDTHHMMSS>.json
    # tag = metadata.get("site_id") or metadata.get("datacenter") or (file_basename or "metrics")
    # ts = metadata.get("timestamp", datetime.utcnow().replace(microsecond=0).isoformat(sep="T"))
    # safe_tag = "".join(c for c in tag if c.isalnum() or c in ("-","_","."))
    # fname = f"{safe_tag}_{ts.replace(':','').replace('-','')}.json"
    # path = os.path.join(_OUTPUT_DIR, fname)
    #
    # tmp = path + ".tmp"
    # with open(tmp, "w", encoding="utf-8") as f:
    #     json.dump(payload, f, ensure_ascii=False, indent=2)
    # os.replace(tmp, path)
    #
    # print(f"External JSON written: {path} (metrics={len(gd_metrics)})")
    # return path
