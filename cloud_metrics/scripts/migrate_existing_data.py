# cloud_metrics/scripts/migrate_existing_data.py

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from cloud_metrics.utils.config import SessionLocal
from cloud_metrics.models.datacenter import Datacenter
from cloud_metrics.models.asset import Asset
from cloud_metrics.models.source import Source
from cloud_metrics.models.metric_definition import MetricDefinition
try:
    from cloud_metrics.models.metric_source_map import MetricSourceMap
except ImportError:
    MetricSourceMap = None
try:
    from cloud_metrics.models.metric_keyword import MetricKeyword
except ImportError:
    MetricKeyword = None
from cloud_metrics.models.cim_mapping import CimMapping
from cloud_metrics.models.unit import QuantityKind, Unit
from cloud_metrics.models.standard_models import Standard, MetricStandardMap
from cloud_metrics.classifiers.alias_classifier import ALIASES
from cloud_metrics.ingestion.semantic_classifier import STANDARDS_MAP

def get_quantity_kind_and_unit_for_key(session, key):
    # Rule-based lookup for quantity kind and canonical unit based on namespace key
    qk_name = None
    unit_sym = None
    
    key_lower = key.lower()
    if "consumption" in key_lower or "renewable" in key_lower:
        qk_name = "Energy"
        unit_sym = "kWh"
    elif "power" in key_lower or "tdp" in key_lower:
        qk_name = "Power"
        unit_sym = "W"
    elif "pue" in key_lower or "utilization" in key_lower or "usage" in key_lower or "wue" in key_lower or "efficiency" in key_lower:
        qk_name = "Percentage"
        unit_sym = "%"
    elif "memory" in key_lower or "traffic" in key_lower or "bytes" in key_lower:
        qk_name = "DataSize"
        unit_sym = "B"
    elif "time" in key_lower or "duration" in key_lower or "suspend" in key_lower or "wallclock" in key_lower:
        qk_name = "Time"
        unit_sym = "s"
    elif "count" in key_lower or "cores" in key_lower or "work" in key_lower or "emissions" in key_lower or "cfp" in key_lower or "ci" in key_lower:
        qk_name = "Count"
        unit_sym = "count"
    elif "temperature" in key_lower or "temp" in key_lower:
        qk_name = "Temperature"
        unit_sym = "°C"
        
    if qk_name and unit_sym:
        qk = session.query(QuantityKind).filter_by(name=qk_name).first()
        u = session.query(Unit).filter_by(symbol=unit_sym).first()
        return qk, u
    return None, None

def migrate_datacenters(session):
    print("Migrating Datacenters to Assets...")
    dcs = session.query(Datacenter).all()
    dc_asset_map = {}
    for dc in dcs:
        asset = session.query(Asset).filter_by(name=dc.name, type="datacenter").first()
        if not asset:
            asset = Asset(
                name=dc.name,
                type="datacenter",
                location=dc.location,
                provider=dc.provider,
                status="active"
            )
            session.add(asset)
            session.flush()
        dc_asset_map[dc.id] = asset.id
    print(f"Migrated {len(dcs)} datacenters.")
    return dc_asset_map

def enrich_metric_definitions(session):
    print("Enriching Metric Definitions with Quantity Kinds & Units...")
    metrics = session.query(MetricDefinition).all()
    enriched_count = 0
    for m in metrics:
        qk, u = get_quantity_kind_and_unit_for_key(session, m.unified_key)
        if qk and u:
            m.quantity_kind_id = qk.id
            m.canonical_unit_id = u.id
            m.status = "active"
            m.metric_type = "observed"
            # Extract simple label
            parts = m.unified_key.split(".")
            m.label = " ".join(parts[1:]).capitalize() if len(parts) > 1 else m.unified_key
            m.domain = parts[1] if len(parts) > 1 else None
            enriched_count += 1
    print(f"Enriched {enriched_count} metric definitions.")

def migrate_metric_source_map(session, file_source_id):
    print("Migrating Metric Source Maps to CimMappings...")
    if MetricSourceMap is None:
        print("Legacy metric_source_map table is dropped. Skipping.")
        return
    try:
        msms = session.query(MetricSourceMap).all()
    except Exception:
        print("Legacy metric_source_map table not found. Skipping.")
        return
    migrated_count = 0
    for msm in msms:
        # Resolve target metric definition
        metric_def = session.query(MetricDefinition).filter_by(unified_key=msm.unified_key).first()
        if not metric_def:
            # Create a basic draft definition if missing
            metric_def = MetricDefinition(unified_key=msm.unified_key, status="draft")
            session.add(metric_def)
            session.flush()
            
        # Check if mapping already exists
        mapping = session.query(CimMapping).filter_by(
            source_key=msm.raw_key,
            cim_metric_id=metric_def.id
        ).first()
        
        if not mapping:
            mapping = CimMapping(
                source_key=msm.raw_key,
                source_id=file_source_id,
                cim_metric_id=metric_def.id,
                relation_type="exactMatch",
                confidence=1.0,
                rationale="Migrated from legacy metric_source_map",
                status="approved",
                origin="seeded"
            )
            session.add(mapping)
            migrated_count += 1
    print(f"Migrated {migrated_count} metric source maps.")

def migrate_metric_keywords(session):
    print("Migrating Metric Keywords to CimMappings...")
    if MetricKeyword is None:
        print("Legacy metric_keywords table is dropped. Skipping.")
        return
    try:
        mks = session.query(MetricKeyword).all()
    except Exception:
        print("Legacy metric_keywords table not found. Skipping.")
        return
    migrated_count = 0
    for mk in mks:
        unified_key = f"gd.{mk.category}.{mk.subcategory}.{mk.short_key}"
        metric_def = session.query(MetricDefinition).filter_by(unified_key=unified_key).first()
        if not metric_def:
            metric_def = MetricDefinition(unified_key=unified_key, status="draft")
            session.add(metric_def)
            session.flush()
            
        # Check if mapping already exists
        mapping = session.query(CimMapping).filter_by(
            source_key=mk.keyword,
            cim_metric_id=metric_def.id
        ).first()
        
        if not mapping:
            mapping = CimMapping(
                source_key=mk.keyword,
                cim_metric_id=metric_def.id,
                relation_type="closeMatch",
                confidence=0.85,
                rationale="Migrated from legacy auto-learned metric_keywords",
                status="approved",
                origin="auto-learned"
            )
            session.add(mapping)
            migrated_count += 1
    print(f"Migrated {migrated_count} metric keywords.")

def migrate_standards_map(session):
    print("Migrating STANDARDS_MAP (semantic classifier) to CimMappings...")
    migrated_count = 0
    for suffix, (org_code, domain, category, metric) in STANDARDS_MAP.items():
        unified_key = f"gd.{domain}.{category}.{metric}"
        metric_def = session.query(MetricDefinition).filter_by(unified_key=unified_key).first()
        if not metric_def:
            metric_def = MetricDefinition(unified_key=unified_key, status="draft")
            session.add(metric_def)
            session.flush()
            
        # Find standard
        std = session.query(Standard).filter(Standard.code.ilike(org_code)).first()
        std_id = std.id if std else None
        
        mapping = session.query(CimMapping).filter_by(
            source_key=suffix,
            cim_metric_id=metric_def.id
        ).first()
        
        if not mapping:
            mapping = CimMapping(
                source_key=suffix,
                cim_metric_id=metric_def.id,
                standard_id=std_id,
                relation_type="exactMatch",
                confidence=1.0,
                rationale="Seeded from legacy semantic classifier STANDARDS_MAP",
                status="approved",
                origin="seeded"
            )
            session.add(mapping)
            migrated_count += 1
    print(f"Migrated {migrated_count} standards map entries.")

def migrate_aliases(session):
    print("Migrating ALIASES (alias classifier) to CimMappings...")
    migrated_count = 0
    for (category, subcategory, short_key), aliases in ALIASES.items():
        # Map back to domain. The category might tell us the domain.
        # Domains: energy, performance, network, storage, environment
        domain = "performance" # default
        if category in ("energy", "network", "storage", "environment"):
            domain = category
            
        unified_key = f"gd.{domain}.{subcategory}.{short_key}"
        metric_def = session.query(MetricDefinition).filter_by(unified_key=unified_key).first()
        if not metric_def:
            metric_def = MetricDefinition(unified_key=unified_key, status="draft")
            session.add(metric_def)
            session.flush()
            
        for alias in aliases:
            mapping = session.query(CimMapping).filter_by(
                source_key=alias,
                cim_metric_id=metric_def.id
            ).first()
            
            if not mapping:
                mapping = CimMapping(
                    source_key=alias,
                    cim_metric_id=metric_def.id,
                    relation_type="closeMatch",
                    confidence=0.9,
                    rationale=f"Seeded from legacy alias classifier for gd.{category}.{subcategory}.{short_key}",
                    status="approved",
                    origin="seeded"
                )
                session.add(mapping)
                migrated_count += 1
    print(f"Migrated {migrated_count} alias entries.")

def main():
    with SessionLocal() as session:
        try:
            # Resolve file_upload source ID
            file_source = session.query(Source).filter_by(name="file_upload").first()
            file_source_id = file_source.id if file_source else None
            
            migrate_datacenters(session)
            enrich_metric_definitions(session)
            migrate_metric_source_map(session, file_source_id)
            migrate_metric_keywords(session)
            migrate_standards_map(session)
            migrate_aliases(session)
            
            session.commit()
            print("Data migration completed successfully!")
        except Exception as e:
            session.rollback()
            print(f"Data migration failed: {e}")
            raise e

if __name__ == '__main__':
    main()
