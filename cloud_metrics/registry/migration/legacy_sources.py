"""Discover legacy raw→unified mapping sources without mutating them."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from cloud_metrics.registry.migration.gd_to_cim import triple_to_gd

logger = logging.getLogger(__name__)

# Accidental site / placeholder keys observed in metric_mapping.json
NOISE_RAW_KEYS = frozenset(
    {
        "30",
        "q",
        "datacenter_A",
        "1-grid-site",
        "eu-central-1-cloud-site",
        "ifca",
    }
)

_REPO_ROOT = Path(__file__).resolve().parents[3]
_MAPPING_JSON = (
    _REPO_ROOT / "cloud_metrics" / "mapping" / "metric_mapping.json"
)
_DATA_MAPPING_JSON = (
    _REPO_ROOT / "cloud_metrics" / "data" / "metric_mapping.json"
)


@dataclass(frozen=True)
class LegacyMappingRecord:
    """One discovered raw_key → legacy unified (gd.*) mapping."""

    raw_key: str
    legacy_unified_key: str
    source_name: str  # e.g. mapping_json, alias_classifier, alias_seeds, data_mapping_json
    confidence: float = 1.0
    category: Optional[str] = None
    subcategory: Optional[str] = None
    short_key: Optional[str] = None
    notes: Optional[str] = None
    unit: Optional[str] = None
    description: Optional[str] = None
    source_system: Optional[str] = None


@dataclass
class DiscoveryReport:
    records: List[LegacyMappingRecord] = field(default_factory=list)
    skipped_noise: int = 0
    skipped_uncategorized: int = 0
    by_source: Dict[str, int] = field(default_factory=dict)

    def add(self, record: LegacyMappingRecord) -> None:
        self.records.append(record)
        self.by_source[record.source_name] = (
            self.by_source.get(record.source_name, 0) + 1
        )


def _is_noise(raw_key: str) -> bool:
    key = (raw_key or "").strip()
    if not key:
        return True
    if key in NOISE_RAW_KEYS:
        return True
    if key.isdigit():
        return True
    if len(key) == 1:
        return True
    return False


def _parse_gd_parts(
    unified_key: str,
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    parts = (unified_key or "").split(".")
    if len(parts) >= 4 and parts[0] == "gd":
        return parts[1], parts[2], ".".join(parts[3:])
    return None, None, None


def _load_runtime_mapping_json(path: Path) -> Dict[str, List[str]]:
    if not path.is_file():
        logger.warning("legacy mapping JSON missing: %s", path)
        return {}
    with path.open(encoding="utf-8") as fh:
        data = json.load(fh) or {}
    out: Dict[str, List[str]] = {}
    for unified, raws in data.items():
        if isinstance(raws, list):
            out[str(unified)] = [str(x) for x in raws]
        elif isinstance(raws, str):
            out[str(unified)] = [raws]
    return out


def _load_data_mapping_json(path: Path) -> Dict[str, str]:
    """Return raw_key → unified_key from exporters format."""
    if not path.is_file():
        return {}
    with path.open(encoding="utf-8") as fh:
        data = json.load(fh) or {}
    mappings = data.get("mappings") or {}
    out: Dict[str, str] = {}
    for raw, meta in mappings.items():
        if isinstance(meta, dict) and meta.get("unified_key"):
            out[str(raw)] = str(meta["unified_key"])
        elif isinstance(meta, str):
            out[str(raw)] = meta
    return out


def _from_mapping_json(report: DiscoveryReport) -> None:
    data = _load_runtime_mapping_json(_MAPPING_JSON)
    for unified, raws in data.items():
        if unified == "gd.uncategorized.unknown.unknown":
            report.skipped_uncategorized += len(raws)
            continue
        cat, sub, short = _parse_gd_parts(unified)
        for raw in raws:
            if _is_noise(raw):
                report.skipped_noise += 1
                continue
            report.add(
                LegacyMappingRecord(
                    raw_key=raw,
                    legacy_unified_key=unified,
                    source_name="mapping_json",
                    # Slightly below alias_seeds so known aliases win over polluted JSON
                    confidence=0.95,
                    category=cat,
                    subcategory=sub,
                    short_key=short,
                    notes="Migrated from cloud_metrics/mapping/metric_mapping.json",
                    source_system="file:metric_mapping.json",
                )
            )


def _from_data_mapping_json(report: DiscoveryReport) -> None:
    data = _load_data_mapping_json(_DATA_MAPPING_JSON)
    for raw, unified in data.items():
        if unified == "gd.uncategorized.unknown.unknown":
            report.skipped_uncategorized += 1
            continue
        if _is_noise(raw):
            report.skipped_noise += 1
            continue
        cat, sub, short = _parse_gd_parts(unified)
        report.add(
            LegacyMappingRecord(
                raw_key=raw,
                legacy_unified_key=unified,
                source_name="data_mapping_json",
                confidence=0.95,
                category=cat,
                subcategory=sub,
                short_key=short,
                notes="Migrated from cloud_metrics/data/metric_mapping.json",
                source_system="file:data/metric_mapping.json",
            )
        )


def _from_alias_classifier(report: DiscoveryReport) -> None:
    try:
        from cloud_metrics.classifiers.alias_classifier import ALIASES
    except Exception as exc:  # pragma: no cover
        logger.warning("alias_classifier unavailable: %s", exc)
        return

    for (cat, sub, short), aliases in ALIASES.items():
        unified = triple_to_gd(cat, sub, short)
        for alias in aliases:
            if _is_noise(alias):
                report.skipped_noise += 1
                continue
            report.add(
                LegacyMappingRecord(
                    raw_key=alias,
                    legacy_unified_key=unified,
                    source_name="alias_classifier",
                    confidence=0.9,
                    category=cat,
                    subcategory=sub,
                    short_key=short,
                    notes="Migrated from classifiers.alias_classifier.ALIASES",
                    source_system="hardcoded:ALIASES",
                )
            )


def _from_alias_seeds(report: DiscoveryReport) -> None:
    try:
        from cloud_metrics.scripts.seed_taxonomy_standards import ALIAS_SEEDS
    except Exception as exc:  # pragma: no cover
        logger.warning("ALIAS_SEEDS unavailable: %s", exc)
        return

    for raw, unified in ALIAS_SEEDS.items():
        if _is_noise(raw):
            report.skipped_noise += 1
            continue
        cat, sub, short = _parse_gd_parts(unified)
        report.add(
            LegacyMappingRecord(
                raw_key=raw,
                legacy_unified_key=unified,
                source_name="alias_seeds",
                confidence=0.99,
                category=cat,
                subcategory=sub,
                short_key=short,
                notes="Migrated from seed_taxonomy_standards.ALIAS_SEEDS",
                source_system="hardcoded:ALIAS_SEEDS",
            )
        )


def _from_standards_map(report: DiscoveryReport) -> None:
    try:
        from cloud_metrics.ingestion.semantic_classifier import STANDARDS_MAP
    except Exception as exc:  # pragma: no cover
        logger.warning("STANDARDS_MAP unavailable: %s", exc)
        return

    for suffix, (_org, domain, cat, metric) in STANDARDS_MAP.items():
        # STANDARDS_MAP values are (org, domain, category, metric) but used as
        # namespace parts: gd.<domain>.<category>.<metric> in semantic path.
        # Historical keys use domain as first taxonomy segment.
        unified = f"gd.{domain}.{cat}.{metric}"
        # Also keep the semantic suffix itself as a discoverable raw key.
        report.add(
            LegacyMappingRecord(
                raw_key=suffix,
                legacy_unified_key=unified,
                source_name="standards_map",
                confidence=0.85,
                category=domain,
                subcategory=cat,
                short_key=metric,
                notes="Migrated from semantic_classifier.STANDARDS_MAP",
                source_system="hardcoded:STANDARDS_MAP",
            )
        )


def _dedupe_prefer_higher_confidence(
    records: Iterable[LegacyMappingRecord],
) -> List[LegacyMappingRecord]:
    """Keep one record per lowercased raw_key (highest confidence wins)."""
    best: Dict[str, LegacyMappingRecord] = {}
    for rec in records:
        key = rec.raw_key.lower()
        prev = best.get(key)
        if prev is None or rec.confidence > prev.confidence:
            best[key] = rec
        elif prev is not None and rec.confidence == prev.confidence:
            # Prefer mapping_json over aliases when tied
            priority = {
                "alias_seeds": 5,
                "alias_classifier": 4,
                "mapping_json": 3,
                "data_mapping_json": 2,
                "standards_map": 1,
            }
            if priority.get(rec.source_name, -1) > priority.get(prev.source_name, -1):
                best[key] = rec
    return list(best.values())


def discover_legacy_mappings(
    *,
    include_mapping_json: bool = True,
    include_data_mapping_json: bool = True,
    include_aliases: bool = True,
    include_alias_seeds: bool = True,
    include_standards_map: bool = True,
    dedupe: bool = True,
) -> DiscoveryReport:
    """Collect legacy mapping records from all known static sources."""
    report = DiscoveryReport()
    if include_mapping_json:
        _from_mapping_json(report)
    if include_data_mapping_json:
        _from_data_mapping_json(report)
    if include_aliases:
        _from_alias_classifier(report)
    if include_alias_seeds:
        _from_alias_seeds(report)
    if include_standards_map:
        _from_standards_map(report)

    if dedupe:
        original = len(report.records)
        report.records = _dedupe_prefer_higher_confidence(report.records)
        logger.info(
            "legacy mapping discovery: %s raw records → %s unique raw keys "
            "(noise_skipped=%s, uncategorized_skipped=%s, by_source=%s)",
            original,
            len(report.records),
            report.skipped_noise,
            report.skipped_uncategorized,
            report.by_source,
        )
        # Rebuild by_source after dedupe
        report.by_source = {}
        for rec in report.records:
            report.by_source[rec.source_name] = (
                report.by_source.get(rec.source_name, 0) + 1
            )
    return report


def mapping_json_path() -> str:
    return str(_MAPPING_JSON)


def data_mapping_json_path() -> str:
    return str(_DATA_MAPPING_JSON)
