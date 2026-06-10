# cloud_metrics/ingestion/automated_mapper.py

import re
from datetime import datetime
from typing import Tuple, Optional

from cloud_metrics.ingestion.semantic_classifier import classify_by_semantics
from cloud_metrics.models.metric_keyword import MetricKeyword
from cloud_metrics.utils.config import SessionLocal

from cloud_metrics.registry.namespace_registry import ensure_gd_namespace
from cloud_metrics.registry.mapping_registry import register_mapping
from cloud_metrics.services.insert_mapped_metric import insert_mapped_metric
from cloud_metrics.services.insert_metric_sample import insert_metric_sample
from cloud_metrics.services.insert_datacenter import get_or_create_datacenter_id
from cloud_metrics.utils.mapping_sync import sync_metric_mapping
from cloud_metrics.utils.unified_key import to_gd
from cloud_metrics.classifiers.alias_classifier import guess_from_alias
from cloud_metrics.classifiers.ensemble_classifier import classify_metric
from cloud_metrics.services.keyword_learning import learn_keyword
from cloud_metrics.utils.partner_payload import parse_partner_payload_generic
from cloud_metrics.classifiers.fallbacks import fallback_namespace_from_raw


_WORD = re.compile(r"[A-Z]?[a-z]+|[0-9]+")

def _tokens(s: str) -> list[str]:
    return [t.lower() for t in _WORD.findall(s)]

def _norm(s: str) -> str:
    """lowercase and keep only a–z0–9;
    join chunks (e.g., 'Disk-ReadOps' -> 'diskreadops')."""
    return "".join(_WORD.findall(s.lower()))

def _infer_unit_from_key(k: str) -> Optional[str]:
    k = k.lower()
    if "kwh" in k or "kilowatthour" in k or k.endswith("_kwh"):
        return "kwh"
    if ("kw" in k or k.endswith("_kw")) and "kwh" not in k:
        return "kw"
    if ("watt" in k or "watts" in k or (k.endswith("_w") or k.endswith("tdp_w"))) and not k.endswith("kw"):
        return "w"
    if "mbps" in k or "kbps" in k or "gbps" in k or "bps" in k:
        return "mbps" if "mbps" in k else "bps"
    if "iops" in k or "ops" in k:
        return "ops"
    if ("bytes" in k or "amountofdatatransferred" in k) or k.endswith("_b"):
        return "bytes"
    if ("cfp" in k or "ci" in k) and k.endswith("_g"):
        return "gco2e"
    if k.endswith("_s"):
        return "s"
    return None

def _classify_to_parts(raw_key: str) -> tuple[str, str, str]:
    key = (raw_key or "").strip()
    toks = set(_tokens(key))

    # 1) standards classifier
    sem = classify_by_semantics(raw_key)
    if sem:
        _, domain, category, metric = sem
        return domain, category, metric

    # 2) DB keywords
    session = SessionLocal()
    try:
        mk = (
            session.query(MetricKeyword)
            .filter((MetricKeyword.keyword == key.lower()) | (MetricKeyword.source_key == key.lower()))
            .first()
        )
        if mk and mk.category and mk.subcategory and mk.short_key:
            return mk.category, mk.subcategory, mk.short_key
    finally:
        session.close()

    # 3) Alias fuzzy match (new!)
    hit = guess_from_alias(key, cutoff=90)
    if hit:
        return hit.category, hit.subcategory, hit.short_key

    # helpers
    any_of = lambda *cands: any(c in toks for c in cands)

    # --- STORAGE ---
    storage_base = any_of("disk","volume","filesystem","fs","storage")
    if storage_base:
        if any_of("read","reads","readops","readiops","readbytes","bytesread","ioread","iopsread"):
            return "storage", "disk", "read_io"
        if any_of("write","writes","writeops","writeiops","writebytes","byteswrite","iowrite","iopswrite"):
            return "storage", "disk", "write_io"
        if any_of("latency","msop","msecop","avgqlen"):
            return "storage", "disk", "latency"
        return "storage", "disk", "usage"

    # --- NETWORK ---
    if any_of("network","traffic","throughput","bandwidth","net","nic","eth"):
        if any_of("in","rx","ingress","receive","inbytes","inpackets"):
            return "network", "traffic", "incoming"
        if any_of("out","tx","egress","transmit","outbytes","outpackets"):
            return "network", "traffic", "outgoing"
        return "network", "traffic", "incoming"

    # --- ENERGY ---
    # consumption (kWh / energy usage)
    if any_of("kwh","kilowatthour","energyconsumed","energyusage","consumption","consumed"):
        return "energy", "consumption", "total"
    # solar / pv
    if any_of("solar","pv","renewable"):
        return "energy", "renewable", "solar"
    # power (W / kW)
    if any_of("power","watt","watts","kw"):
        return "energy", "power", "total"

    # --- ENVIRONMENT ---
    if any_of("temperature","temp","celsius"):
        return "environment", "temperature", "ambient"
    if any_of("temperature","temp","celsius") and any_of("exterior","ext"):
        return "environment", "temperature", "exterior"
    if any_of("temperature","temp","celsius") and any_of("interior","int"):
        return "environment", "temperature", "interior"

    # --- PERFORMANCE ---
    if any_of("cpu","processor"):
        return "performance", "cpu", "utilization"
    if any_of("memory","mem","ram"):
        return "performance", "memory", "usage"

    return "uncategorized", "unknown", "unknown"


def process_metric_sample(
        *,
        raw_key: str,
        value: float,
        origin: str,
        captured_at: Optional[datetime] = None,
        ri_id: Optional[str] = None,
        node_id: Optional[str] = None,
        vm_id: Optional[str] = None,
        host: Optional[str] = None,
        site_id: Optional[str] = None,
        extra_meta: Optional[dict] = None,
        domain: Optional[str] = None,

) -> str:
    """
    Ingest a single metric (raw_key + value) from a given origin (filename/datacenter).
    1) classify -> (category, subcategory, short_key)
    2) generate_namespace -> standard.category.subcategory.short_key (DB-driven)
    3) persist MetricDefinition (sources = [origin or filename], tags)
    4) sync metric_mapping.json with raw_key (not origin)
    """
    # 1) Normalizing
    raw_key_norm = (raw_key or "").strip()
    origin_label = (origin or "unknown").strip()

    try:
        dc_id = get_or_create_datacenter_id(origin_label)
    except Exception:
        origin_label = origin_label or "unknown"
        dc_id = get_or_create_datacenter_id(origin_label)

    # 3) Classify with Ensemble
    d = classify_metric(raw_key)    #Decision (cat, subcat, key, conf., rationale)
    category, subcategory, short_key = d.category, d.subcategory, d.short_key

    # 2) storing units before classification
    unit = _infer_unit_from_key(_norm(raw_key))
    tags = [category, subcategory, short_key]

    # 4) Checking for unknown
    if category == "uncategorized" or subcategory == "unknown":
        try:
            from cloud_metrics.classifiers.fallbacks import fallback_namespace_from_raw
            category, subcategory, short_key = fallback_namespace_from_raw(raw_key_norm, unit_hint=unit)
        except Exception:
            category, subcategory, short_key = ("custom", "unknown", "".join(_tokens(raw_key_norm)) or "unknown")

    # 5) Prefix gd.* Taxonomy
    try:
        unified_key = ensure_gd_namespace(d.category, d.subcategory, d.short_key, auto_create=True)
    except Exception as e:
        print(f" Namespace missing: cat='{category}', subcat='{subcategory}' → {e}")
        unified_key = f"gd.{category.lower()}.{subcategory.lower()}.{short_key.lower()}"
        unified_key = to_gd(unified_key) # Hard-normalizing to gd.* in case anything upstream was odd

    # 6) Auto-learn if confident enough
    try:
        if (d.confidence or 0) >= 0.85 and category != "uncategorized" and subcategory != "unknown":
            learn_keyword(raw_key, d.category, d.subcategory, d.short_key, d.confidence)
            from cloud_metrics.classifiers import ensemble_classifier as EC
            if hasattr(EC.classify_metric, "cache_clear"):
                EC.classify_metric.cache_clear()
    except Exception as _e:
        pass

    # 7) Persist registry state (definitions, source map, json mapping)
    try:
        register_mapping(
            datacenter_id=dc_id,
            raw_key=raw_key,
            unified_key=unified_key,
            origin=origin,
            value=value,
            unit=unit,
            tags=[d.category, d.subcategory, d.short_key],
        )
    except Exception as _e:
        try:
            sync_metric_mapping(unified_key=unified_key, source_key=raw_key_norm)
        except Exception:
            pass

    # 8) Persisting sources to be the file/datacenter name (origin), not the raw metric key
    insert_mapped_metric(unified_key=unified_key, source_keys=[origin], tags=tags)

    # per-DC sample row
    insert_metric_sample(
        datacenter_id=dc_id,
        unified_key=unified_key,
        raw_key=raw_key_norm,
        value=value,
        unit=unit,
        tags={},
        source_file=origin_label,
        captured_at=captured_at or datetime.utcnow(),
        ri_id=ri_id,
        node_id=node_id,
        vm_id=vm_id,
        host=host,
        site_id=site_id,
        clf_confidence=getattr (d, "confidence", None),
        clf_rationale=getattr(d, "rationale", None),
        extra_meta=extra_meta,
        domain=domain,
    )

    # JSON sync must record raw_key → unified_key (not origin)
    try:
        sync_metric_mapping(unified_key=unified_key, source_key=raw_key)
    except Exception as e:
        print(f"JSON sync failed for {raw_key} → {unified_key}: {e}")

    return unified_key

def process_new_raw_metric(raw_key: str) -> str:
    return process_metric_sample(raw_key=raw_key, value=0.0, origin="unknown")