"""Idempotent loader for Milestone 3 ``cim_*`` registry seed data."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from cloud_metrics.models.cim_registry import (
    CimEvidenceRequirement,
    CimLifecycleStage,
    CimMetricDefinition,
    CimMetricLifecycleLink,
    CimMetricMapping,
    CimProvenanceRecord,
    CimQuantityKind,
    CimSource,
    CimStandard,
    CimUnit,
    CimValidationRule,
)
from cloud_metrics.registry.seed import data as seed_data


@dataclass
class SeedReport:
    """Counts of created vs already-present rows."""

    created: Dict[str, int] = field(default_factory=dict)
    existing: Dict[str, int] = field(default_factory=dict)

    def bump(self, key: str, *, created: bool) -> None:
        bucket = self.created if created else self.existing
        bucket[key] = bucket.get(key, 0) + 1

    def as_dict(self) -> Dict[str, Any]:
        return {"created": dict(self.created), "existing": dict(self.existing)}


def _approved_kwargs() -> Dict[str, Any]:
    return {
        "status": "approved",
        "review_status": "approved",
        "version": 1,
        "created_by": seed_data.CREATED_BY,
        "confidence_score": 1.0,
    }


def seed_quantity_kinds(session: Session, report: SeedReport) -> Dict[str, CimQuantityKind]:
    by_name: Dict[str, CimQuantityKind] = {}
    for item in seed_data.QUANTITY_KINDS:
        row = session.query(CimQuantityKind).filter_by(name=item["name"]).first()
        if row:
            report.bump("quantity_kinds", created=False)
        else:
            row = CimQuantityKind(
                name=item["name"],
                description=item.get("description"),
                qudt_uri=item.get("qudt_uri"),
                **_approved_kwargs(),
            )
            session.add(row)
            session.flush()
            report.bump("quantity_kinds", created=True)
        by_name[row.name] = row
    return by_name


def seed_units(
    session: Session,
    report: SeedReport,
    quantity_kinds: Dict[str, CimQuantityKind],
) -> Dict[str, CimUnit]:
    by_symbol: Dict[str, CimUnit] = {}

    # Pass 1: canonical units (symbol == canonical_symbol)
    for symbol, (name, qk_name, si_base, canon_sym, factor, offset) in seed_data.UNITS.items():
        if symbol != canon_sym:
            continue
        row = session.query(CimUnit).filter_by(symbol=symbol).first()
        if row:
            report.bump("units", created=False)
        else:
            row = CimUnit(
                symbol=symbol,
                name=name,
                quantity_kind_id=quantity_kinds[qk_name].id,
                si_base=si_base,
                canonical_unit_id=None,
                conversion_factor=factor,
                conversion_offset=offset,
                **_approved_kwargs(),
            )
            session.add(row)
            session.flush()
            report.bump("units", created=True)
        by_symbol[symbol] = row

    # Pass 2: non-canonical units
    for symbol, (name, qk_name, si_base, canon_sym, factor, offset) in seed_data.UNITS.items():
        if symbol == canon_sym:
            continue
        row = session.query(CimUnit).filter_by(symbol=symbol).first()
        if row:
            report.bump("units", created=False)
        else:
            canon = by_symbol[canon_sym]
            row = CimUnit(
                symbol=symbol,
                name=name,
                quantity_kind_id=quantity_kinds[qk_name].id,
                si_base=si_base,
                canonical_unit_id=canon.id,
                conversion_factor=factor,
                conversion_offset=offset,
                **_approved_kwargs(),
            )
            session.add(row)
            session.flush()
            report.bump("units", created=True)
        by_symbol[symbol] = row

    return by_symbol


def seed_lifecycle_stages(
    session: Session, report: SeedReport
) -> Dict[str, CimLifecycleStage]:
    by_key: Dict[str, CimLifecycleStage] = {}
    for item in seed_data.LIFECYCLE_STAGES:
        row = (
            session.query(CimLifecycleStage)
            .filter_by(stage_key=item["stage_key"])
            .first()
        )
        if row:
            report.bump("lifecycle_stages", created=False)
        else:
            row = CimLifecycleStage(
                stage_key=item["stage_key"],
                name=item["name"],
                label=item.get("label"),
                description=item.get("description"),
                sequence=item.get("sequence"),
                **_approved_kwargs(),
            )
            session.add(row)
            session.flush()
            report.bump("lifecycle_stages", created=True)
        by_key[row.stage_key] = row
    return by_key


def seed_standards(session: Session, report: SeedReport) -> Dict[str, CimStandard]:
    by_code: Dict[str, CimStandard] = {}
    for item in seed_data.STANDARDS:
        row = (
            session.query(CimStandard)
            .filter_by(code=item["code"], standard_version=item.get("standard_version"))
            .first()
        )
        if row is None:
            # Fallback: match by code alone for idempotency if version string drifts
            row = session.query(CimStandard).filter_by(code=item["code"]).first()
        if row:
            report.bump("standards", created=False)
        else:
            row = CimStandard(
                code=item["code"],
                name=item["name"],
                standard_version=item.get("standard_version"),
                description=item.get("description"),
                vocabulary_type=item.get("vocabulary_type"),
                namespace_prefix=item.get("namespace_prefix"),
                namespace_uri=item.get("namespace_uri"),
                domain=item.get("domain"),
                **_approved_kwargs(),
            )
            session.add(row)
            session.flush()
            report.bump("standards", created=True)
        by_code[row.code] = row
    return by_code


def seed_bootstrap_source(session: Session, report: SeedReport) -> CimSource:
    cfg = seed_data.SEED_SOURCE
    row = (
        session.query(CimSource)
        .filter_by(name=cfg["name"], type=cfg["type"])
        .first()
    )
    if row:
        report.bump("sources", created=False)
        return row
    row = CimSource(
        name=cfg["name"],
        type=cfg["type"],
        protocol=cfg.get("protocol"),
        format=cfg.get("format"),
        schema_version=cfg.get("schema_version"),
        auth_method=cfg.get("auth_method", "none"),
        notes=cfg.get("notes"),
        status=cfg.get("status", "approved"),
        review_status=cfg.get("review_status", "approved"),
        version=1,
        created_by=seed_data.CREATED_BY,
        confidence_score=1.0,
    )
    session.add(row)
    session.flush()
    report.bump("sources", created=True)
    return row


def seed_metrics(
    session: Session,
    report: SeedReport,
    quantity_kinds: Dict[str, CimQuantityKind],
    units: Dict[str, CimUnit],
) -> Dict[str, CimMetricDefinition]:
    by_ns: Dict[str, CimMetricDefinition] = {}
    for item in seed_data.METRICS:
        row = (
            session.query(CimMetricDefinition)
            .filter_by(namespace=item["namespace"])
            .first()
        )
        if row:
            report.bump("metrics", created=False)
        else:
            qk = quantity_kinds[item["quantity_kind"]]
            unit = units[item["canonical_unit"]]
            row = CimMetricDefinition(
                namespace=item["namespace"],
                label=item.get("label"),
                description=item.get("description"),
                domain=item.get("domain"),
                category=item.get("category"),
                subcategory=item.get("subcategory"),
                quantity_kind_id=qk.id,
                canonical_unit_id=unit.id,
                metric_type=item.get("metric_type"),
                notes=item.get("notes"),
                tags=[item.get("domain"), item.get("category"), item.get("subcategory")],
                **_approved_kwargs(),
            )
            session.add(row)
            session.flush()
            report.bump("metrics", created=True)
        by_ns[row.namespace] = row
    return by_ns


def seed_metric_lifecycle_links(
    session: Session,
    report: SeedReport,
    metrics: Dict[str, CimMetricDefinition],
    stages: Dict[str, CimLifecycleStage],
) -> None:
    for namespace, links in seed_data.METRIC_LIFECYCLE_LINKS.items():
        metric = metrics[namespace]
        for stage_key, relevance in links:
            stage = stages[stage_key]
            existing = (
                session.query(CimMetricLifecycleLink)
                .filter_by(metric_id=metric.id, lifecycle_stage_id=stage.id)
                .first()
            )
            if existing:
                report.bump("metric_lifecycle_links", created=False)
                continue
            session.add(
                CimMetricLifecycleLink(
                    metric_id=metric.id,
                    lifecycle_stage_id=stage.id,
                    relevance=relevance,
                    **_approved_kwargs(),
                )
            )
            report.bump("metric_lifecycle_links", created=True)
    session.flush()


def seed_standard_mappings(
    session: Session,
    report: SeedReport,
    metrics: Dict[str, CimMetricDefinition],
    standards: Dict[str, CimStandard],
    source: CimSource,
) -> None:
    for namespace, std_code, relation, suffix, rationale in seed_data.STANDARD_MAPPINGS:
        metric = metrics[namespace]
        standard = standards[std_code]
        source_key = f"std:{std_code}:{suffix}:{namespace}"
        existing = (
            session.query(CimMetricMapping)
            .filter_by(source_key=source_key, source_id=source.id)
            .first()
        )
        if existing:
            report.bump("standard_mappings", created=False)
            continue
        session.add(
            CimMetricMapping(
                source_key=source_key,
                source_id=source.id,
                metric_id=metric.id,
                standard_id=standard.id,
                relation_type=relation,
                rationale=rationale,
                origin="seeded",
                approved_by=seed_data.CREATED_BY,
                **_approved_kwargs(),
            )
        )
        report.bump("standard_mappings", created=True)
    session.flush()


def seed_validation_rules(session: Session, report: SeedReport) -> None:
    for item in seed_data.VALIDATION_RULES:
        row = session.query(CimValidationRule).filter_by(name=item["name"]).first()
        if row:
            report.bump("validation_rules", created=False)
            continue
        session.add(
            CimValidationRule(
                name=item["name"],
                description=item.get("description"),
                rule_type=item["rule_type"],
                target_registry=item["target_registry"],
                condition=item.get("condition") or {},
                severity=item.get("severity", "error"),
                **_approved_kwargs(),
            )
        )
        report.bump("validation_rules", created=True)
    session.flush()


def seed_evidence_requirements(
    session: Session,
    report: SeedReport,
    metrics: Dict[str, CimMetricDefinition],
    standards: Dict[str, CimStandard],
) -> None:
    for item in seed_data.EVIDENCE_REQUIREMENTS:
        metric = metrics[item["metric_namespace"]]
        standard = standards[item["standard_code"]]
        existing = (
            session.query(CimEvidenceRequirement)
            .filter_by(
                standard_id=standard.id,
                metric_id=metric.id,
                evidence_type=item["evidence_type"],
            )
            .first()
        )
        if existing:
            report.bump("evidence_requirements", created=False)
            continue
        session.add(
            CimEvidenceRequirement(
                standard_id=standard.id,
                metric_id=metric.id,
                evidence_type=item["evidence_type"],
                requirement_level=item.get("requirement_level", "recommended"),
                reporting_period=item.get("reporting_period"),
                aggregation_method=item.get("aggregation_method"),
                boundary=item.get("boundary"),
                description=item.get("description"),
                **_approved_kwargs(),
            )
        )
        report.bump("evidence_requirements", created=True)
    session.flush()


def seed_bootstrap_provenance(session: Session, report: SeedReport) -> None:
    """Single idempotent provenance marker for the seed bootstrap activity."""
    existing = (
        session.query(CimProvenanceRecord)
        .filter_by(
            entity_type="registry_seed",
            activity="bootstrap",
            agent=seed_data.CREATED_BY,
            method="seed_cim_registries",
        )
        .first()
    )
    if existing:
        report.bump("provenance_records", created=False)
        return
    session.add(
        CimProvenanceRecord(
            entity_type="registry_seed",
            entity_id=None,
            activity="bootstrap",
            agent=seed_data.CREATED_BY,
            method="seed_cim_registries",
            inputs={"milestone": 3},
            outputs={"relation_types": list(seed_data.RELATION_TYPES)},
            notes="Milestone 3 controlled registry seed applied.",
            **_approved_kwargs(),
        )
    )
    report.bump("provenance_records", created=True)
    session.flush()


def seed_all(session: Session, *, commit: bool = True) -> SeedReport:
    """Load all Milestone 3 seed catalogues into ``cim_*`` tables.

    Safe to call repeatedly: unique natural keys are checked before insert.
    """
    report = SeedReport()
    quantity_kinds = seed_quantity_kinds(session, report)
    units = seed_units(session, report, quantity_kinds)
    stages = seed_lifecycle_stages(session, report)
    standards = seed_standards(session, report)
    source = seed_bootstrap_source(session, report)
    metrics = seed_metrics(session, report, quantity_kinds, units)
    seed_metric_lifecycle_links(session, report, metrics, stages)
    seed_standard_mappings(session, report, metrics, standards, source)
    seed_validation_rules(session, report)
    seed_evidence_requirements(session, report, metrics, standards)
    seed_bootstrap_provenance(session, report)
    if commit:
        session.commit()
    else:
        session.flush()
    return report
