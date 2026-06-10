# cloud_metrics/ingestion/automated_mapper.py

import re
from datetime import datetime
from typing import Tuple, Optional
from sqlalchemy import func

from cloud_metrics.ingestion.semantic_classifier import classify_by_semantics
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
from cloud_metrics.models.asset import Asset
from cloud_metrics.models.source import Source
from cloud_metrics.models.metric_definition import MetricDefinition
from cloud_metrics.models.unit import Unit


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
    if ("wh" in k or "watthour" in k or k.endswith("_wh")) and "kwh" not in k:
        return "wh"
    if ("kw" in k or k.endswith("_kw")) and "kwh" not in k and "wh" not in k:
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

    # 2) DB keywords (from Mapping Registry / CimMapping)
    session = SessionLocal()
    try:
        from cloud_metrics.models.cim_mapping import CimMapping
        mapping = (
            session.query(CimMapping)
            .filter(func.lower(CimMapping.source_key) == key.lower())
            .first()
        )
        if mapping and mapping.cim_metric:
            parts = mapping.cim_metric.unified_key.split(".")
            if len(parts) >= 4:
                return parts[1], parts[2], parts[3]
    except Exception:
        pass
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
    1) Classify using Ensemble & Mapping Registry.
    2) Normalize unit and value using Unit Registry conversion rules.
    3) Run validation rules from Rule Registry.
    4) Persist metric sample.
    5) Log activity provenance in Provenance Registry.
    """
    raw_key_norm = (raw_key or "").strip()
    origin_label = (origin or "unknown").strip()
    original_value = value

    # 1) Get/Create Datacenter and Asset
    try:
        dc_id = get_or_create_datacenter_id(origin_label)
    except Exception:
        origin_label = origin_label or "unknown"
        dc_id = get_or_create_datacenter_id(origin_label)

    # Asset Registry link
    with SessionLocal() as session:
        asset = session.query(Asset).filter_by(name=origin_label, type="datacenter").first()
        if not asset:
            asset = Asset(name=origin_label, type="datacenter", status="active")
            session.add(asset)
            session.commit()
            
        # Source Registry lookup
        source_name = "file_upload"
        if "aws" in origin_label.lower():
            source_name = "aws_cloudwatch"
        elif "gcp" in origin_label.lower():
            source_name = "gcp_monitoring"
            
        source = session.query(Source).filter_by(name=source_name).first()
        source_id = source.id if source else None

    # 2) Classify with Ensemble (which checks Mapping Registry first)
    d = classify_metric(raw_key_norm)
    category, subcategory, short_key = d.category, d.subcategory, d.short_key
    raw_unit = _infer_unit_from_key(_norm(raw_key_norm))

    # 3) Check for fallback/unknown taxonomy
    if category == "uncategorized" or subcategory == "unknown":
        try:
            from cloud_metrics.classifiers.fallbacks import fallback_namespace_from_raw
            category, subcategory, short_key = fallback_namespace_from_raw(raw_key_norm, unit_hint=raw_unit)
        except Exception:
            category, subcategory, short_key = ("custom", "unknown", "".join(_tokens(raw_key_norm)) or "unknown")

    # 4) Prefix taxonomy
    try:
        unified_key = ensure_gd_namespace(category, subcategory, short_key, auto_create=True)
    except Exception as e:
        unified_key = f"gd.{category.lower()}.{subcategory.lower()}.{short_key.lower()}"
        unified_key = to_gd(unified_key)

    # 5) Auto-learn mapping if confident and not already in Mapping Registry
    from cloud_metrics.services.mapping_registry_service import resolve_mapping, auto_learn_mapping
    existing_mapping = resolve_mapping(raw_key_norm)
    if not existing_mapping and (d.confidence or 0) >= 0.85 and category != "uncategorized" and subcategory != "unknown":
        try:
            auto_learn_mapping(raw_key_norm, unified_key, d.confidence, d.rationale)
        except Exception:
            pass

    # 6) Unit Normalization and Conversion
    final_value = value
    final_unit = raw_unit
    
    with SessionLocal() as session:
        metric_def = session.query(MetricDefinition).filter_by(unified_key=unified_key).first()
        if metric_def and metric_def.canonical_unit_id:
            canonical_unit = session.query(Unit).get(metric_def.canonical_unit_id)
            if canonical_unit and raw_unit and canonical_unit.symbol.lower() != raw_unit.lower():
                # Map raw unit to standard symbol casing
                raw_unit_standardized = session.query(Unit).filter(func.lower(Unit.symbol) == raw_unit.lower()).first()
                if raw_unit_standardized:
                    try:
                        from cloud_metrics.services.unit_registry_service import convert_value
                        converted_value = convert_value(value, raw_unit_standardized.symbol, canonical_unit.symbol)
                        
                        # Log provenance for unit conversion
                        from cloud_metrics.services.provenance_registry_service import record_activity
                        record_activity(
                            entity_type="metric_sample",
                            activity="unit_conversion",
                            agent="pipeline_unit_normalizer",
                            inputs={"value": value, "unit": raw_unit_standardized.symbol},
                            outputs={"value": converted_value, "unit": canonical_unit.symbol},
                            method="convert_value",
                            confidence=1.0
                        )
                        
                        final_value = converted_value
                        final_unit = canonical_unit.symbol
                    except Exception as e:
                        print(f"Unit conversion failed from {raw_unit} to {canonical_unit.symbol}: {e}")

    # 7) Validation Rules check
    from cloud_metrics.services.rule_registry_service import validate_metric_sample
    violations = validate_metric_sample(
        unified_key=unified_key,
        value=final_value,
        unit=final_unit,
        tags={"region": site_id or "unknown"}
    )
    if violations:
        print(f"Validation warnings/errors for {unified_key}: {violations}")
        try:
            from cloud_metrics.services.provenance_registry_service import record_activity
            record_activity(
                entity_type="metric_sample",
                activity="validation",
                agent="rule_registry_service",
                inputs={"unified_key": unified_key, "value": final_value, "unit": final_unit},
                outputs={"violations": violations},
                method="validate_metric_sample",
                confidence=1.0
            )
        except Exception:
            pass

    # 8) Persist registry state (definitions, source map, json mapping)
    try:
        register_mapping(
            datacenter_id=dc_id,
            raw_key=raw_key_norm,
            unified_key=unified_key,
            origin=origin,
            value=final_value,
            unit=final_unit,
            tags=[category, subcategory, short_key],
        )
    except Exception:
        try:
            sync_metric_mapping(unified_key=unified_key, source_key=raw_key_norm)
        except Exception:
            pass

    # Back-compat registry insert
    insert_mapped_metric(unified_key=unified_key, source_keys=[origin_label], tags=[category, subcategory, short_key])

    # 9) Insert Metric Sample
    sample_id = insert_metric_sample(
        datacenter_id=dc_id,
        unified_key=unified_key,
        raw_key=raw_key_norm,
        value=final_value,
        unit=final_unit,
        tags={},
        source_file=origin_label,
        captured_at=captured_at or datetime.utcnow(),
        ri_id=ri_id,
        node_id=node_id,
        vm_id=vm_id,
        host=host,
        site_id=site_id,
        clf_confidence=getattr(d, "confidence", None),
        clf_rationale=getattr(d, "rationale", None),
        extra_meta=extra_meta,
        domain=domain,
    )

    # Log ingestion provenance
    try:
        from cloud_metrics.services.provenance_registry_service import record_activity
        record_activity(
            entity_type="metric_sample",
            entity_id=sample_id,
            activity="ingestion",
            agent="automated_mapper_pipeline",
            inputs={"raw_key": raw_key, "raw_value": original_value, "origin": origin_label},
            outputs={"unified_key": unified_key, "value": final_value, "unit": final_unit},
            method="process_metric_sample",
            confidence=getattr(d, "confidence", 1.0)
        )
    except Exception:
        pass

    # JSON sync must record raw_key → unified_key
    try:
        sync_metric_mapping(unified_key=unified_key, source_key=raw_key_norm)
    except Exception as e:
        print(f"JSON sync failed for {raw_key_norm} → {unified_key}: {e}")

    return unified_key

def process_new_raw_metric(raw_key: str) -> str:
    return process_metric_sample(raw_key=raw_key, value=0.0, origin="unknown")