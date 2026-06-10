# cloud_metrics/services/standards_registry.py
from __future__ import annotations
from typing import Optional, Tuple, Iterable
from sqlalchemy import func

from cloud_metrics.utils.config import SessionLocal
from cloud_metrics.models.standard_models import Standard, MetricStandardMap
from cloud_metrics.models.metric_definition import MetricDefinition

# map basic perf metrics to JRC-CoC (low confidence)? set True if you want that:
MAP_PERF_TO_JRC = True


def ensure_seed_standards() -> None:
    """Idempotently ensure the standards catalog exists (codes MUST match your DB)."""
    SEED_STANDARDS = [
        ("TGG-PUE", "The Green Grid PUE", "https://www.thegreengrid.org/en/resources", "Power Usage Effectiveness"),
        ("TGG-WUE", "The Green Grid WUE", "https://www.thegreengrid.org/en/resources", "Water Usage Effectiveness"),
        ("GHG", "Greenhouse Gas Protocol", "https://ghgprotocol.org", "Emissions / CO2e / CFP"),
        ("ISO-50001", "ISO 50001", "https://www.iso.org/standard/69426.html", "Energy management systems"),
        ("ASHRAE-90.4-2022", "Energy Standard for Data Centers",
         "https://www.ashrae.org/technical-resources/standards-and-guidelines/read-only-versions-of-ashrae-standards",
         "Minimum energy-efficiency requirements for data centers."),
        ("ASHRAE-TC9.9-2021", "Thermal Guidelines for Data Processing Environments (5th ed.)",
         "https://www.ashrae.org/file%20library/technical%20resources/bookstore/supplemental%20files/therm-gdlns-5th-r-e-refcard.pdf",
         "Recommended thermal/humidity envelopes & classes for IT equipment."),
        ("JRC-CoC-2025", "EU Code of Conduct for Data Centre Energy Efficiency — Best Practice Guidelines",
         "https://publications.jrc.ec.europa.eu/repository/handle/JRC141521",
         "Best practice measures to reduce DC energy use."),
        ("IEEE-802.3az-2010", "Energy Efficient Ethernet",
         "https://standards.ieee.org/ieee/802.3az/4270/", "EEE / LPI"),
        ("IEEE-1459-2025", "Standard Definitions for the Measurement of Electric Power Quantities",
         "https://standards.ieee.org/ieee/1459/7578/", "Power definitions"),
        ("IEEE-1547-2018", "Interconnection of Distributed Energy Resources with Electric Power Systems",
         "https://standards.ieee.org/standard/1547-2018.html", "DER interconnection"),
        ("IETF", "Internet Engineering Task Force", "https://www.ietf.org/", "Networking metrics (generic)"),
        ("SNIA", "Storage Networking Industry Association", "https://www.snia.org/", "Storage performance metrics"),
    ]
    with SessionLocal() as s:
        for code, name, url, desc in SEED_STANDARDS:
            if not s.query(Standard).filter(func.lower(Standard.code) == code.lower()).first():
                s.add(Standard(code=code, name=name, url=url, description=desc))
        s.commit()


def _normalize_for_rules(uk: str) -> str:
    """Allow legacy prefixes (iso., ieee., jrc., ashrae.) to be evaluated by the same ruleset."""
    parts = (uk or "").split(".")
    if len(parts) >= 4 and parts[0].lower() != "gd":
        return "gd." + ".".join(parts[1:4])
    return uk


def _guess_standard_codes(unified_key: str) -> Iterable[tuple[str, Optional[str], float, str]]:
    """
    Yield (standard_code, standard_metric_code, confidence, rationale) for zero/one/many matches.
    """
    if not unified_key:
        return []
    key = _normalize_for_rules(unified_key).lower()
    parts = key.split(".")
    if len(parts) < 4 or parts[0] != "gd":
        return []

    _, cat, sub, short = parts[:4]

    # ---- Specific rules FIRST ----
    if cat == "energy" and sub == "efficiency" and short == "pue":
        yield ("TGG-PUE", "PUE", 0.99, "alias:pue")
    if cat == "environment" and sub == "water" and short == "wue":
        yield ("TGG-WUE", "WUE", 0.99, "alias:wue")
    if cat == "environment" and sub == "emissions":
        yield ("GHG", short.upper(), 0.85, "env:emissions")
    if cat == "environment" and sub == "temperature":
        yield ("ASHRAE-TC9.9-2021", None, 0.8, "thermal guidelines")
    if cat == "energy" and sub == "power" and short == "total":
        yield ("IEEE-1459-2025", "Power", 0.7, "power-def")
    if cat == "energy" and sub == "renewable" and short == "solar":
        yield ("IEEE-1547-2018", "DER", 0.5, "der interconnect")
    if cat == "network" and sub == "traffic":
        yield ("IETF", None, 0.6, "network:traffic")
    if cat == "storage" and sub == "disk":
        yield ("SNIA", None, 0.6, "storage:disk")
    if MAP_PERF_TO_JRC and cat == "performance" and (sub, short) in {("cpu", "utilization"), ("memory", "usage")}:
        yield ("JRC-CoC-2025", None, 0.4, "best-practice mapping")

    # ---- Umbrella rules LAST ----
    if cat == "energy":
        yield ("ISO-50001", None, 0.6, "energy domain")


def attach_standard(unified_key: str) -> None:
    """Attach zero/one/many standards to a metric_definition if we can infer them."""
    ensure_seed_standards()
    with SessionLocal() as s:
        md = (s.query(MetricDefinition)
              .filter(func.lower(MetricDefinition.unified_key) == unified_key.lower())
              .first())
        if not md:
            return

        for std_code, std_metric_code, conf, why in _guess_standard_codes(unified_key):
            std = s.query(Standard).filter(func.lower(Standard.code) == std_code.lower()).first()
            if not std:
                continue

            link = (s.query(MetricStandardMap)
                    .filter(MetricStandardMap.metric_definition_id == md.id,
                            MetricStandardMap.standard_id == std.id)
                    .first())

            if link:
                if conf is not None and (link.confidence or 0.0) < conf:
                    link.confidence = conf
                    link.rationale = why
            else:
                s.add(MetricStandardMap(
                    metric_definition_id=md.id,
                    standard_id=std.id,
                    standard_metric_code=std_metric_code,
                    confidence=conf,
                    rationale=why,
                ))
        s.commit()
