# cloud_metrics/scripts/seed_registries.py

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from cloud_metrics.utils.config import SessionLocal
from cloud_metrics.models.unit import QuantityKind, Unit
from cloud_metrics.models.source import Source
from cloud_metrics.models.standard_models import Standard

def seed_quantity_kinds_and_units(session):
    print("Seeding Quantity Kinds and Units...")
    
    # 1. Quantity Kinds
    qk_data = {
        "Energy": ("Energy consumption", "http://qudt.org/vocab/quantitykind/Energy"),
        "Power": ("Electric power", "http://qudt.org/vocab/quantitykind/Power"),
        "Temperature": ("Thermodynamic temperature", "http://qudt.org/vocab/quantitykind/Temperature"),
        "DataSize": ("Digital data size", "http://qudt.org/vocab/quantitykind/InformationEntropy"),
        "DataRate": ("Data transfer rate", "http://qudt.org/vocab/quantitykind/DataRate"),
        "Percentage": ("Ratio or percentage", "http://qudt.org/vocab/quantitykind/DimensionlessRatio"),
        "Time": ("Duration or time period", "http://qudt.org/vocab/quantitykind/Time"),
        "Count": ("Discrete count of objects", "http://qudt.org/vocab/quantitykind/Dimensionless")
    }
    
    qk_objs = {}
    for name, (desc, uri) in qk_data.items():
        qk = session.query(QuantityKind).filter_by(name=name).first()
        if not qk:
            qk = QuantityKind(name=name, description=desc, qudt_uri=uri)
            session.add(qk)
            session.flush() # get ID
        qk_objs[name] = qk

    # 2. Units (with canonical mapping and conversion factor/offset)
    # Format: symbol: (name, quantity_kind, si_base, canonical_symbol, factor, offset)
    units_data = {
        # Energy (Canonical: kWh)
        "kWh": ("kilowatt-hour", "Energy", False, "kWh", 1.0, 0.0),
        "Wh": ("watt-hour", "Energy", False, "kWh", 0.001, 0.0),
        "MWh": ("megawatt-hour", "Energy", False, "kWh", 1000.0, 0.0),
        "J": ("joule", "Energy", True, "kWh", 2.77778e-7, 0.0),
        "kJ": ("kilojoule", "Energy", False, "kWh", 2.77778e-4, 0.0),
        "MJ": ("megajoule", "Energy", False, "kWh", 0.277778, 0.0),
        
        # Power (Canonical: W)
        "W": ("watt", "Power", True, "W", 1.0, 0.0),
        "kW": ("kilowatt", "Power", False, "W", 1000.0, 0.0),
        "MW": ("megawatt", "Power", False, "W", 1000000.0, 0.0),
        "VA": ("volt-ampere", "Power", False, "W", 1.0, 0.0),
        "kVA": ("kilovolt-ampere", "Power", False, "W", 1000.0, 0.0),
        
        # Temperature (Canonical: °C)
        "°C": ("degree Celsius", "Temperature", False, "°C", 1.0, 0.0),
        "°F": ("degree Fahrenheit", "Temperature", False, "°C", 5/9, -160/9),
        "K": ("kelvin", "Temperature", True, "°C", 1.0, -273.15),
        
        # DataSize (Canonical: B)
        "B": ("byte", "DataSize", True, "B", 1.0, 0.0),
        "KB": ("kilobyte", "DataSize", False, "B", 1024.0, 0.0),
        "MB": ("megabyte", "DataSize", False, "B", 1024.0**2, 0.0),
        "GB": ("gigabyte", "DataSize", False, "B", 1024.0**3, 0.0),
        "TB": ("terabyte", "DataSize", False, "B", 1024.0**4, 0.0),
        "PB": ("petabyte", "DataSize", False, "B", 1024.0**5, 0.0),
        
        # DataRate (Canonical: bps)
        "bps": ("bits per second", "DataRate", True, "bps", 1.0, 0.0),
        "Kbps": ("kilobits per second", "DataRate", False, "bps", 1000.0, 0.0),
        "Mbps": ("megabits per second", "DataRate", False, "bps", 1000000.0, 0.0),
        "Gbps": ("gigabits per second", "DataRate", False, "bps", 1000000000.0, 0.0),
        
        # Percentage (Canonical: %)
        "%": ("percent", "Percentage", False, "%", 1.0, 0.0),
        
        # Time (Canonical: s)
        "s": ("second", "Time", True, "s", 1.0, 0.0),
        "ms": ("millisecond", "Time", False, "s", 0.001, 0.0),
        "min": ("minute", "Time", False, "s", 60.0, 0.0),
        "h": ("hour", "Time", False, "s", 3600.0, 0.0),
        "d": ("day", "Time", False, "s", 86400.0, 0.0),
        
        # Count (Canonical: count)
        "count": ("count", "Count", True, "count", 1.0, 0.0),
        "cores": ("CPU cores count", "Count", False, "count", 1.0, 0.0)
    }

    # First insert all canonical units (those where symbol == canonical_symbol)
    unit_objs = {}
    for symbol, (name, qk_name, si_base, canon_sym, factor, offset) in units_data.items():
        if symbol == canon_sym:
            u = session.query(Unit).filter_by(symbol=symbol).first()
            if not u:
                u = Unit(
                    symbol=symbol,
                    name=name,
                    quantity_kind_id=qk_objs[qk_name].id,
                    si_base=si_base,
                    conversion_factor=factor,
                    conversion_offset=offset
                )
                session.add(u)
                session.flush()
            unit_objs[symbol] = u

    # Next insert non-canonical units mapping to canonical ones
    for symbol, (name, qk_name, si_base, canon_sym, factor, offset) in units_data.items():
        if symbol != canon_sym:
            u = session.query(Unit).filter_by(symbol=symbol).first()
            if not u:
                u = Unit(
                    symbol=symbol,
                    name=name,
                    quantity_kind_id=qk_objs[qk_name].id,
                    si_base=si_base,
                    canonical_unit_id=unit_objs[canon_sym].id,
                    conversion_factor=factor,
                    conversion_offset=offset
                )
                session.add(u)
                session.flush()
            unit_objs[symbol] = u

def seed_sources(session):
    print("Seeding Sources...")
    sources = [
        ("aws_cloudwatch", "api", "HTTPS", "JSON", "none", "active"),
        ("gcp_monitoring", "api", "HTTPS", "JSON", "none", "active"),
        ("prometheus", "prometheus", "HTTP", "Prometheus exposition", "none", "active"),
        ("file_upload", "file", "file", "JSON/YAML/CSV/XML", "none", "active"),
        ("manual", "manual", "web", "JSON", "none", "active")
    ]
    
    for name, type_, proto, fmt, auth, status in sources:
        s = session.query(Source).filter_by(name=name).first()
        if not s:
            s = Source(
                name=name,
                type=type_,
                protocol=proto,
                format=fmt,
                auth_method=auth,
                status=status
            )
            session.add(s)

def seed_additional_standards(session):
    print("Seeding Additional Standards...")
    # Seed new standards that might be missing
    standards = [
        ("SAREF", "Smart Applications REference Ontology", "https://saref.etsi.org/", "Ontology representing smart devices and energy"),
        ("QUDT", "Quantity, Unit, Dimension and Type", "http://qudt.org/", "Ontology representing quantities, units, and dimensions"),
        ("PROV-O", "PROV Ontology", "https://www.w3.org/TR/prov-o/", "W3C standard for provenance logs and audit trail"),
        ("OTel", "OpenTelemetry Semantic Conventions", "https://opentelemetry.io/docs/specs/semconv/", "Semantic conventions for monitoring and cloud metrics")
    ]
    
    for code, name, url, desc in standards:
        std = session.query(Standard).filter_by(code=code).first()
        if not std:
            std = Standard(code=code, name=name, url=url, description=desc)
            session.add(std)

def main():
    with SessionLocal() as session:
        try:
            seed_quantity_kinds_and_units(session)
            seed_sources(session)
            seed_additional_standards(session)
            session.commit()
            print("Seeding completed successfully!")
        except Exception as e:
            session.rollback()
            print(f"Seeding failed: {e}")
            raise e

if __name__ == '__main__':
    main()
