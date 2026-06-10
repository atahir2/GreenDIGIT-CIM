# cloud_metrics/utils/ingest_any.py

from __future__ import annotations
import os, json, re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Tuple, Iterable, Optional

# optional deps (install if not present): pyyaml, xmltodict
try:
    import yaml
except Exception:
    yaml = None
try:
    import xmltodict
except Exception:
    xmltodict = None

_WORD = re.compile(r"[A-Z]?[a-z]+|[0-9]+")
TS_KEYS = {"timestamp","captured_at","observed_at","event_end_timestamp","event_start_timestamp","startexectime","stopexectime"}
DC_KEYS = {"datacenter","data_center","site","facility","dc","provider","region","location","site_description"}
SITEID_KEYS = {"site_id","siteid","executionid","execution_id","node_id","vm_id"}
META_EXCLUDE = DC_KEYS | SITEID_KEYS | TS_KEYS | {"owner","status","cloud_type","compute_service","networktype","measurementtype","destinationexecunitid","site_type"}

NUM_RE = re.compile(r"""
    (?P<num>
      [-+]?
      (?:
        (?:\d{1,3}(?:[ ,]\d{3})+|\d+)
        (?:\.\d+)? |
        \.\d+
      )
      (?:[eE][-+]?\d+)?
    )
""", re.VERBOSE)

def _tokens(s: str) -> list[str]:
    return [t.lower() for t in _WORD.findall(s or "")]

def _slug(s: str) -> str:
    t = "-".join(_tokens(s))
    return t or "unknown"

def _iso(x: Any) -> Optional[datetime]:
    if not x: return None
    try:
        return datetime.fromisoformat(str(x).replace("Z","+00:00"))
    except Exception:
        return None

def _looks_numeric(v: Any) -> bool:
    return isinstance(v, (int, float)) or (isinstance(v, str) and re.fullmatch(r"[-+]?\d+(\.\d+)?", v.strip() or "") is not None)

def _to_float(v: Any) -> Optional[float]:
    try:
        return float(v)
    except Exception:
        return None

@dataclass
class PartnerMeta:
    domain: str                  # 'cloud'|'grid'|'network'|'iot'|'unknown'
    datacenter: str              # slug: e.g., 'aws-eu-central-1'
    site_id: str                 # stable id for samples
    captured_at: Optional[datetime]
    ri_id: Optional[str] = None
    node_id: Optional[str] = None
    vm_id: Optional[str] = None
    host: Optional[str] = None
    extra: Optional[Dict[str, Any]] = None

# ---------------- core API ----------------

def load_any_file(path: str) -> Tuple[PartnerMeta, Dict[str, float]]:
    """
    Load JSON/YAML/XML/CSV/TXT and extract (PartnerMeta, metrics dict).
    Never raises for unknown structure; falls back to reasonable defaults.
    """
    ext = os.path.splitext(path)[1].lower()
    stem = os.path.basename(path).rsplit(".",1)[0]

    if ext in {".json",".yml",".yaml",".xml"}:
        doc = _load_structured(path, ext)
        meta, metrics = _extract_from_mapping(doc)
    elif ext == ".csv":
        meta, metrics = _extract_from_csv(path, stem)
    elif ext == ".txt":
        meta, metrics = _extract_from_txt(path, stem)
    else:
        raise ValueError(f"Unsupported file type: {ext}")

    # fallback datacenter/site_id if missing
    if not meta.datacenter:
        meta.datacenter = _slug(stem)
    if not meta.site_id:
        meta.site_id = f"{meta.datacenter}.default_node.default_vm"

    return meta, metrics

# ---------------- structured loaders ----------------

def _load_structured(path: str, ext: str) -> Dict[str, Any]:
    if ext == ".json":
        with open(path,"r",encoding="utf-8-sig") as f:
            return json.load(f)
    if ext in {".yml",".yaml"}:
        if not yaml: raise RuntimeError("pyyaml not installed")
        with open(path,"r",encoding="utf-8") as f:
            return yaml.safe_load(f)
    if ext == ".xml":
        if not xmltodict: raise RuntimeError("xmltodict not installed")
        with open(path,"r",encoding="utf-8") as f:
            xml = xmltodict.parse(f.read())
        # convert xmltodict nested OrderedDicts to plain dicts
        return json.loads(json.dumps(xml))
    raise ValueError(f"Unhandled structured ext: {ext}")

# ---------------- deep utils ----------------

def _deep_items(obj: Any, prefix: tuple[str,...]=()) -> Iterable[tuple[tuple[str,...], Any]]:
    """Yield (path_tuple, value) for every leaf (dict/list)."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            kstr = str(k)
            yield from _deep_items(v, prefix + (kstr,))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _deep_items(v, prefix + (str(i),))
    else:
        yield (prefix, obj)

def _deep_first_str(obj: Any, keyset: set[str]) -> Optional[str]:
    """Return first non-empty string for any key whose last token matches keyset."""
    for path, v in _deep_items(obj):
        if not path: continue
        key = path[-1].lower()
        if key in keyset and isinstance(v, str) and v.strip():
            return v.strip()
    return None

def _deep_first_time(obj: Any) -> Optional[datetime]:
    for path, v in _deep_items(obj):
        if not path: continue
        if path[-1].lower() in TS_KEYS:
            t = _iso(v)
            if t: return t
    return None

def _deep_numeric_map(obj: Any) -> Dict[str, float]:
    """Flatten all numeric leaves to 'a.b.c' keys, skipping obvious meta keys."""
    out: Dict[str, float] = {}
    for path, v in _deep_items(obj):
        if not path: continue
        last = path[-1].lower()
        if last in META_EXCLUDE:
            continue
        val = _to_float(v)
        if val is not None:
            key = ".".join(path)
            out[key] = val
    return out

def _infer_domain(doc: Dict[str, Any]) -> str:
    # look across all keys
    keys = set(k.lower() for k,_ in _deep_items(doc) if k)
    if any("networktype" in k or "amountofdatatransferred" in k for k in keys):
        return "network"
    if any("ncores" in k or "tdp_w" in k or "normcputime_s" in k for k in keys):
        return "grid"
    if any("cloud_type" in k or "compute_service" in k for k in keys):
        return "cloud"
    return "unknown"


# ---------------- extraction strategies for mapping-like docs ----------------

def _extract_from_mapping(doc: Any) -> Tuple[PartnerMeta, Dict[str,float]]:
    if not isinstance(doc, dict):
        # if top-level is list, try to fold it
        if isinstance(doc, list) and doc and isinstance(doc[0], dict):
            doc = {"records": doc}
        else:
            doc = {}

    # Strategy A: partner generic (site_type + fact/detail)
    if "site_type" in doc or "fact" in doc or "detail" in doc:
        return _from_partner_generic(doc)

    # Strategy B: legacy {"metadata": {...}, "metrics": {...}}
    if "metadata" in doc and "metrics" in doc and isinstance(doc["metadata"], dict) and isinstance(doc["metrics"], dict):
        md = doc["metadata"]
        dc = str(md.get("datacenter") or "").strip()
        site = str(md.get("site_id") or "").strip()
        cap = _iso(md.get("timestamp"))
        meta = PartnerMeta(
            domain=str(md.get("domain") or "unknown"),
            datacenter=_slug(dc) if dc else "",
            site_id=site or "",
            captured_at=cap,
            ri_id=md.get("ri_id"), node_id=md.get("node_id"), vm_id=md.get("vm_id"), host=md.get("host"),
            extra={k:v for k,v in md.items() if k not in {"datacenter","site_id","timestamp","ri_id","node_id","vm_id","host","domain"}}
        )
        metrics = { str(k): _to_float(v) for k,v in doc["metrics"].items() if _looks_numeric(v) }
        return meta, {k:v for k,v in metrics.items() if v is not None}

    # Strategy C: # generic deep scan
    dc_guess = _deep_first_str(doc, DC_KEYS) or ""
    site_guess = _deep_first_str(doc, SITEID_KEYS) or ""
    cap = _deep_first_time(doc)
    metrics = _deep_numeric_map(doc)
    domain = _infer_domain(doc)
    meta = PartnerMeta(
            domain=domain,
            datacenter=_slug(dc_guess) if dc_guess else "",
            site_id=site_guess or "",
            captured_at=cap,
            extra=None,
    )

    # Fallback: empty metrics
    return meta, metrics

def _from_partner_generic(doc: Dict[str, Any]) -> Tuple[PartnerMeta, Dict[str,float]]:
    site_type = str(doc.get("site_type") or "").strip().lower() or "unknown"
    fact = doc.get("fact") or {}
    detail = doc.get("detail") or {}

    # datacenter from site_description or fact.site
    site_descr = str(doc.get("site_description") or fact.get("site") or "").strip()
    dc_slug = _slug(site_descr) if site_descr else f"{site_type}-unknown"

    # timestamps
    cap = _iso(fact.get("event_end_timestamp") or fact.get("stopexectime"))

    # execunit/site_id best effort
    execunit = str(fact.get("execunitid") or detail.get("execunitid") or "").strip() or None
    site_id = f"{dc_slug}.{execunit}" if execunit else f"{dc_slug}.default_node.default_vm"

    # harvest numerics from fact + detail
    metrics = _deep_numeric_map(fact)
    metrics.update({k: v for k, v in _deep_numeric_map(detail).items() if k not in metrics})

    # keep useful non-numeric flags into extra
    keep = ["job_finished","execunitfinished","status","owner","cloud_type","compute_service","networktype","measurementtype","destinationexecunitid","site","site_type"]
    extra = {}
    for path, v in _deep_items({"fact": fact, "detail": detail}):
        if not path: continue
        last = path[-1].lower()
        if last in keep and isinstance(v, (str, int, float, bool)):
            extra[".".join(path)] = v
    extra["site_description"] = site_descr
    extra["window"] = {
        "start": fact.get("event_start_timestamp") or fact.get("startexectime"),
        "end":   fact.get("event_end_timestamp")   or fact.get("stopexectime"),
    }

    return PartnerMeta(
        domain=site_type, datacenter=dc_slug, site_id=site_id, captured_at=cap, extra=extra or None
    ), metrics

# def _guess_meta(doc: Dict[str, Any]) -> PartnerMeta:
#     # datacenter guess
#     dc = (doc.get("datacenter") or doc.get("dc") or doc.get("site") or doc.get("facility") or "")
#     dc_slug = _slug(str(dc)) if dc else ""
#
#     # domain clue
#     keys = set(k.lower() for k in doc.keys())
#     if "cloud_type" in keys or "compute_service" in keys:
#         domain = "cloud"
#     elif "networktype" in keys or "amountofdatatransferred" in keys:
#         domain = "network"
#     elif "ncores" in keys or "tdp_w" in keys or "normcputime_s" in keys:
#         domain = "grid"
#     else:
#         domain = "unknown"
#
#     # timestamp guess
#     cap = None
#     for k in TS_KEYS:
#         cap = _iso(doc.get(k))
#         if cap: break
#
#     return PartnerMeta(domain=domain, datacenter=dc_slug, site_id="", captured_at=cap, extra=None)

def _harvest_numerics(d: Dict[str, Any]) -> Dict[str, float]:
    out: Dict[str, float] = {}
    for k, v in d.items():
        if _looks_numeric(v):
            fv = _to_float(v)
            if fv is not None:
                out[str(k)] = fv
    return out

# ---------------- CSV & TXT ----------------

import csv

def _extract_from_csv(path: str, stem: str) -> Tuple[PartnerMeta, Dict[str,float]]:
    """
    Supports two shapes:
    1) Key,Value rows (first col name, second numeric value)
    2) Wide table: header are metric names; take the last row (or the only row)
    Tries to pull datacenter/site_id/timestamp from columns if present.
    """
    metrics: Dict[str, float] = {}
    dc_slug = ""
    site_id = ""
    cap: Optional[datetime] = None
    domain = "unknown"

    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = list(csv.reader(f))
        if not reader:
            return PartnerMeta(domain=domain, datacenter="", site_id="", captured_at=None), {}

        # detect key-value style
        if len(reader[0]) in (2,3):
            for row in reader:
                if not row: continue
                key = (row[0] or "").strip()
                val = row[1] if len(row) > 1 else None
                if key.lower() in {"datacenter","site","dc"}:
                    dc_slug = _slug(val or "")
                elif key.lower() in {"site_id","siteid"}:
                    site_id = str(val or "").strip()
                elif key.lower() in TS_KEYS:
                    cap = _iso(val)
                elif _looks_numeric(val):
                    fv = _to_float(val)
                    if fv is not None:
                        metrics[key] = fv
        else:
            # wide: first row header
            header = [h.strip() for h in reader[0]]
            data_rows = reader[1:]
            if not data_rows:
                return PartnerMeta(domain=domain, datacenter="", site_id="", captured_at=None), {}
            last = data_rows[-1]
            for i, col in enumerate(header):
                val = last[i] if i < len(last) else None
                if col.lower() in {"datacenter","site","dc"}:
                    dc_slug = _slug(val or "")
                elif col.lower() in {"site_id","siteid"}:
                    site_id = str(val or "").strip()
                elif col.lower() in TS_KEYS:
                    cap = _iso(val)
                elif _looks_numeric(val):
                    fv = _to_float(val)
                    if fv is not None:
                        metrics[col] = fv

    if not site_id:
        site_id = f"{dc_slug or _slug(stem)}.default_node.default_vm"

    return PartnerMeta(domain=domain, datacenter=dc_slug or _slug(stem), site_id=site_id, captured_at=cap), metrics

def _extract_from_txt(path: str, stem: str) -> Tuple[PartnerMeta, Dict[str,float]]:
    """
    Key=Value lines; picks numerics as metrics; grabs dc/site_id/timestamp if present.
    """
    metrics: Dict[str, float] = {}
    dc_slug = ""
    site_id = ""
    cap: Optional[datetime] = None
    with open(path,"r",encoding="utf-8-sig") as f:
        for line in f:
            if "=" not in line: continue
            k, v = [p.strip() for p in line.split("=",1)]
            kl = k.lower()
            if kl in {"datacenter","site","dc"}:
                dc_slug = _slug(v)
            elif kl in {"site_id","siteid"}:
                site_id = v
            elif kl in TS_KEYS:
                cap = _iso(v)
            elif _looks_numeric(v):
                fv = _to_float(v)
                if fv is not None:
                    metrics[k] = fv
    if not dc_slug:
        dc_slug = _slug(stem)
    if not site_id:
        site_id = f"{dc_slug or _slug(stem)}.default_node.default_vm"
    return PartnerMeta(domain="unknown", datacenter=dc_slug or _slug(stem), site_id=site_id, captured_at=cap), metrics
