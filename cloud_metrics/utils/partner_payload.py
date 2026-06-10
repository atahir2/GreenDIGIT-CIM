# cloud_metrics/utils/partner_payload.py

from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Tuple
import re

_WORD = re.compile(r"[A-Z]?[a-z]+|[0-9]+")

def _tokens(s: str) -> list[str]:
    return [t.lower() for t in _WORD.findall(s or "")]

def _iso(x: Any) -> datetime | None:
    if not x: return None
    try:
        return datetime.fromisoformat(str(x).replace("Z","+00:00"))
    except Exception:
        return None

def _slug(s: str) -> str:
    t = "-".join(_tokens(s))
    return t or "unknown"

@dataclass
class PartnerMeta:
    domain: str                  # 'cloud'|'grid'|'network'|...
    datacenter: str              # slug, e.g., 'aws-eu-central-1', 'infn-t1', 'garr-milan'
    site_id: str                 # derived (see per-domain rules below)
    captured_at: datetime | None
    ri_id: str | None = None
    node_id: str | None = None
    vm_id: str | None = None
    host: str | None = None
    extra: Dict[str, Any] | None = None

def parse_partner_payload_generic(doc: Dict[str, Any]) -> Tuple[PartnerMeta, Dict[str,float]]:
    """
    Accepts Cloud/Grid/Network samples shaped like your files:
      - top-level: site_type, site_description, fact{...}, detail{...}
    Extracts metadata, derives datacenter + site_id, collects numeric metrics from fact & detail.
    """
    if not isinstance(doc, dict):
        raise ValueError("JSON root must be an object")

    site_type = str(doc.get("site_type") or "").strip().lower() or "unknown"
    site_descr = str(doc.get("site_description") or doc.get("fact", {}).get("site") or "").strip()
    fact = doc.get("fact") or {}
    detail = doc.get("detail") or {}

    # time window
    t_end  = _iso(fact.get("event_end_timestamp")  or fact.get("stopexectime"))

    # keep full window in extra
    window = {
        "start": fact.get("event_start_timestamp") or fact.get("startexectime"),
        "end":   fact.get("event_end_timestamp")   or fact.get("stopexectime"),
    }

    # derive datacenter (slug from site_description/fact.site)
    dc_slug = _slug(site_descr) if site_descr else f"{site_type}-unknown"

    # ids available?
    execunit = str(fact.get("execunitid") or "").strip() or None

    # per-domain site_id policy
    if site_type in {"cloud","grid","network"}:
        # dc.execunitid if present; else fallback to default composite
        site_id = f"{dc_slug}.{execunit}" if execunit else f"{dc_slug}.default_node.default_vm"
    else:
        site_id = f"{dc_slug}.default_node.default_vm"

    # collect metrics: numeric leaves from fact + detail
    metrics: Dict[str, float] = {}
    def _harvest(d: Dict[str, Any]):
        for k, v in d.items():
            if isinstance(v, (int, float)):
                metrics[str(k)] = float(v)
    if isinstance(fact, dict): _harvest(fact)
    if isinstance(detail, dict): _harvest(detail)

    # build extra meta (non-numeric / useful context)
    keep_keys = [
        "job_finished","execunitfinished","status","owner",
        "cloud_type","compute_service","networktype","measurementtype",
        "destinationexecunitid","site","site_type",
    ]
    extra: Dict[str, Any] = {k: fact[k] for k in keep_keys if k in fact}
    extra.update({k: detail[k] for k in keep_keys if k in detail})
    extra["site_description"] = site_descr
    extra["window"] = window

    meta = PartnerMeta(
        domain=site_type,
        datacenter=dc_slug,
        site_id=site_id,
        captured_at=t_end,
        extra=extra or None,
    )
    return meta, metrics
