"""CIM registry export service (Milestone 15).

Read-only interoperability layer over existing registries. Does not mutate
CIM tables, does not replace the internal model, and does not rewrite
candidate/under_review status as approved.
"""

from __future__ import annotations

import csv
import io
import logging
from typing import Any, Dict, Iterable, List, Optional, Sequence

from sqlalchemy.orm import Session

from cloud_metrics.registry.evidence import EvidenceRegistryService
from cloud_metrics.registry.extension import ExtensionRegistryService
from cloud_metrics.registry.lifecycle import LifecycleRegistryService
from cloud_metrics.registry.provenance import ProvenanceRegistryService
from cloud_metrics.registry.standards import StandardsRegistryService
from cloud_metrics.registry.export.types import (
    APPROVED_STATUSES,
    CANDIDATE_STATUSES,
    CSV_DATASETS,
    JSONLD_CONTEXT,
    PROFILE_CROSSWALK,
    PROFILE_CSV,
    PROFILE_DCAT,
    PROFILE_EVIDENCE,
    PROFILE_JSON,
    PROFILE_JSONLD,
    PROFILE_PROVENANCE,
    PROFILE_ROCRATE,
    RELATION_TO_JSONLD,
    ROCRATE_CONTEXT,
    DcatExportRequest,
    WorkflowRunExportRequest,
    compliance_block,
    isoformat,
    utcnow,
)

logger = logging.getLogger(__name__)

METRIC_CATALOGUE_COLUMNS = (
    "namespace",
    "label",
    "description",
    "domain",
    "category",
    "subcategory",
    "quantity_kind",
    "canonical_unit",
    "metric_type",
    "status",
    "review_status",
    "version",
)

MAPPING_COLUMNS = (
    "source_key",
    "cim_namespace",
    "relation_type",
    "confidence_score",
    "status",
    "review_status",
    "origin",
    "rationale",
    "standard_code",
    "standard_term",
)

CROSSWALK_COLUMNS = (
    "cim_namespace",
    "standard",
    "standard_term",
    "relation_type",
    "confidence_score",
    "review_status",
    "notes",
    "status",
)

EVIDENCE_CSV_COLUMNS = (
    "reportable_metric",
    "required_evidence",
    "available_evidence",
    "missing_evidence",
    "readiness_status",
    "requirement_level",
    "standard_code",
    "lifecycle_context",
    "reporting_context",
)

EXTENSION_COLUMNS = (
    "metric_namespace",
    "raw_metric_name",
    "status",
    "review_status",
    "proposed_standard",
    "justification",
    "confidence_score",
)


def _status_of(row: Any, default: str = "draft") -> str:
    return (getattr(row, "status", None) or default).lower()


def _review_of(row: Any, default: str = "pending") -> str:
    return (getattr(row, "review_status", None) or default).lower()


def _is_approved(status: Optional[str]) -> bool:
    return (status or "").lower() in APPROVED_STATUSES


def _csv_text(columns: Sequence[str], rows: Iterable[Dict[str, Any]]) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(columns), extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow({k: "" if row.get(k) is None else row.get(k) for k in columns})
    return buf.getvalue()


class ExportService:
    """Registry-driven export / interoperability service."""

    def __init__(self, session: Optional[Session] = None) -> None:
        self._session = session
        self._standards = StandardsRegistryService(session=session)
        self._evidence = EvidenceRegistryService(session=session)
        self._lifecycle = LifecycleRegistryService(session=session)
        self._provenance = ProvenanceRegistryService(session=session)
        self._extension = ExtensionRegistryService(session=session)

    # ------------------------------------------------------------------
    # JSON
    # ------------------------------------------------------------------

    def export_json(
        self,
        *,
        kpi_results: Optional[List[Dict[str, Any]]] = None,
        include_candidates: bool = True,
    ) -> Dict[str, Any]:
        """Full native JSON dump of exportable CIM registry slices."""
        metrics = self._collect_metrics(include_candidates=include_candidates)
        return {
            "format": "json",
            "profile": PROFILE_JSON,
            "compliance": compliance_block("json"),
            "metric_definitions": metrics,
            "metric_mappings": self._collect_mappings(),
            "standards_mappings": self._collect_crosswalk_rows(),
            "lifecycle_mappings": self._collect_lifecycle_links(),
            "evidence_requirements": self._collect_evidence_requirements(),
            "provenance_records": self._collect_provenance_records(),
            "extension_candidates": self._collect_extensions(),
            "kpi_results": list(kpi_results or []),
        }

    def export_metrics_json(self, *, include_candidates: bool = True) -> Dict[str, Any]:
        """JSON focused on metric definitions (used by tests / API)."""
        return {
            "format": "json",
            "profile": PROFILE_JSON,
            "compliance": compliance_block("json"),
            "metric_definitions": self._collect_metrics(
                include_candidates=include_candidates
            ),
        }

    # ------------------------------------------------------------------
    # CSV
    # ------------------------------------------------------------------

    def export_csv(self, dataset: str) -> str:
        key = (dataset or "").strip().lower()
        aliases = {
            "metric": "metrics",
            "metric_catalogue": "metrics",
            "catalogue": "metrics",
            "mapping": "mappings",
            "mapping_registry": "mappings",
            "crosswalk": "standards",
            "standards_crosswalk": "standards",
            "evidence_readiness": "evidence",
            "extension": "extensions",
            "extension_candidate": "extensions",
            "extension_candidates": "extensions",
        }
        key = aliases.get(key, key)
        if key not in CSV_DATASETS:
            raise ValueError(
                f"unknown CSV dataset '{dataset}'; expected one of {CSV_DATASETS}"
            )
        if key == "metrics":
            return self.export_metric_catalogue_csv()
        if key == "mappings":
            return self.export_mapping_registry_csv()
        if key == "standards":
            return self.export_standards_crosswalk_csv()
        if key == "evidence":
            return self.export_evidence_readiness_csv()
        return self.export_extension_candidate_csv()

    def export_metric_catalogue_csv(self) -> str:
        return _csv_text(METRIC_CATALOGUE_COLUMNS, self._collect_metrics())

    def export_mapping_registry_csv(self) -> str:
        return _csv_text(MAPPING_COLUMNS, self._collect_mappings())

    def export_standards_crosswalk_csv(self) -> str:
        return _csv_text(CROSSWALK_COLUMNS, self._collect_crosswalk_rows())

    def export_evidence_readiness_csv(
        self,
        *,
        available_evidence: Optional[Dict[str, List[str]]] = None,
    ) -> str:
        rows: List[Dict[str, Any]] = []
        for metric in self._collect_metrics():
            payload = self.export_evidence_readiness(
                metric_namespace=metric["namespace"],
                available_evidence=(available_evidence or {}).get(metric["namespace"]),
            )
            required = payload.get("required_evidence") or []
            if not required:
                continue
            for req in required:
                rows.append(
                    {
                        "reportable_metric": payload["reportable_metric"],
                        "required_evidence": req.get("description")
                        or req.get("evidence_type"),
                        "available_evidence": "; ".join(
                            payload.get("available_evidence") or []
                        ),
                        "missing_evidence": "; ".join(
                            payload.get("missing_evidence") or []
                        ),
                        "readiness_status": payload.get("readiness_status"),
                        "requirement_level": req.get("requirement_level"),
                        "standard_code": req.get("standard_code"),
                        "lifecycle_context": "; ".join(
                            payload.get("lifecycle_context") or []
                        ),
                        "reporting_context": payload.get("reporting_context") or "",
                    }
                )
        return _csv_text(EVIDENCE_CSV_COLUMNS, rows)

    def export_extension_candidate_csv(self) -> str:
        return _csv_text(EXTENSION_COLUMNS, self._collect_extensions())

    # ------------------------------------------------------------------
    # JSON-LD (partial)
    # ------------------------------------------------------------------

    def export_jsonld(
        self,
        metric_namespace: Optional[str] = None,
        *,
        include_all_metrics: bool = False,
    ) -> Dict[str, Any]:
        """Lightweight JSON-LD for one metric, or a graph of all metrics."""
        if include_all_metrics and not metric_namespace:
            entities = [
                self._metric_jsonld_entity(m["namespace"])
                for m in self._collect_metrics()
            ]
            return {
                "@context": JSONLD_CONTEXT,
                "@graph": [e for e in entities if e],
                "compliance": compliance_block("jsonld"),
                "profile": PROFILE_JSONLD,
            }

        ns = metric_namespace or "cim:energy.efficiency.pue"
        entity = self._metric_jsonld_entity(ns)
        doc = {
            "@context": JSONLD_CONTEXT,
            "compliance": compliance_block("jsonld"),
            "profile": PROFILE_JSONLD,
        }
        doc.update(entity)
        return doc

    def _metric_jsonld_entity(self, namespace: str) -> Dict[str, Any]:
        metric = self._get_metric_row(namespace)
        if metric is None:
            return {
                "@id": self._metric_iri(namespace),
                "@type": ["schema:PropertyValue", "cim:MetricDefinition"],
                "identifier": namespace,
                "status": "unknown",
                "reviewStatus": "unknown",
                "message": "metric not found",
            }

        status = _status_of(metric, "draft")
        review = _review_of(metric, "pending")
        qk = getattr(metric, "quantity_kind", None)
        unit = getattr(metric, "canonical_unit", None)
        qk_name = qk.name if qk is not None else None
        qk_uri = getattr(qk, "qudt_uri", None) if qk is not None else None
        unit_symbol = unit.symbol if unit is not None else None
        unit_uri = getattr(unit, "qudt_uri", None) if unit is not None else None

        mappings: List[Dict[str, Any]] = []
        if _is_approved(status):
            std = self._standards.get_mappings_for_metric(
                metric.namespace, allow_approved=True
            )
            for m in std.mappings:
                mappings.append(
                    {
                        "@type": "cim:StandardsMapping",
                        "standard": m.standard_code,
                        "standardTerm": m.standard_term or m.standard_term_code,
                        "relationType": m.relation_type,
                        "mappingPredicate": RELATION_TO_JSONLD.get(
                            m.relation_type or "", "cim:mappingRelation"
                        ),
                        "confidenceScore": m.confidence_score,
                        "reviewStatus": m.review_status,
                        "notes": m.notes,
                    }
                )
        else:
            logger.info(
                "JSON-LD: suppressing approved standards for non-approved metric %s",
                metric.namespace,
            )

        sources = list(metric.sources or []) if getattr(metric, "sources", None) else []
        provenance_ref = None
        if metric.id is not None:
            chain = self._provenance.get_chain("metric_definition", metric.id)
            if chain:
                last = chain[-1]
                provenance_ref = {
                    "@id": f"cim:provenance/{last.id}",
                    "@type": "prov:Entity",
                    "prov:wasGeneratedBy": last.activity,
                    "prov:wasAttributedTo": last.agent,
                }

        entity: Dict[str, Any] = {
            "@id": self._metric_iri(metric.namespace),
            "@type": ["schema:PropertyValue", "cim:MetricDefinition"],
            "identifier": metric.namespace,
            "name": metric.label,
            "description": metric.description,
            "unitCode": unit_symbol,
            "quantityKind": qk_name,
            "status": status,
            "reviewStatus": review,
            "domain": metric.domain,
            "metricType": metric.metric_type,
        }
        if qk_uri:
            entity["qudt:hasQuantityKind"] = {"@id": qk_uri}
        if unit_uri:
            entity["qudt:hasUnit"] = {"@id": unit_uri}
        if sources:
            entity["sourceContext"] = sources
        if mappings:
            entity["standardsMappings"] = mappings
        if provenance_ref:
            entity["provenance"] = provenance_ref
        else:
            entity["provenance"] = None
        return entity

    @staticmethod
    def _metric_iri(namespace: str) -> str:
        slug = (namespace or "").replace("cim:", "")
        return f"cim:metric/{slug}"

    # ------------------------------------------------------------------
    # RO-Crate-style
    # ------------------------------------------------------------------

    def export_rocrate_style(
        self,
        request: WorkflowRunExportRequest,
        *,
        kpi_results: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """RO-Crate-style reproducibility package for a workflow run.

        Labelled as RO-Crate-style / RO-Crate-ready. Not a fully validated
        RO-Crate 1.1 crate.
        """
        energy_ns = "cim:workflow.energy.per_run"
        carbon_ns = "cim:workflow.carbon.per_run"
        duration_ns = "cim:workflow.execution.duration"

        energy_metric = self._metric_jsonld_entity(energy_ns)
        carbon_metric = self._metric_jsonld_entity(carbon_ns)
        duration_metric = self._metric_jsonld_entity(duration_ns)

        std_energy = self._standards.get_mappings_for_metric(
            energy_ns, allow_approved=True
        )
        std_carbon = self._standards.get_mappings_for_metric(
            carbon_ns, allow_approved=True
        )

        prov_records = self._collect_provenance_records()
        # Prefer records that mention this run if present
        run_id = request.workflow_run_id
        related_prov = [
            r
            for r in prov_records
            if run_id
            and (
                run_id in str(r.get("inputs") or "")
                or run_id in str(r.get("outputs") or "")
                or run_id in str(r.get("notes") or "")
            )
        ]

        crate_id = "./"
        metadata_id = "ro-crate-metadata.json"
        run_id_frag = f"#workflow-run/{request.workflow_run_id}"
        wf_id_frag = f"#workflow/{request.workflow_id}"

        parts: List[Dict[str, Any]] = [
            {"@id": run_id_frag},
            {"@id": wf_id_frag},
            {"@id": self._metric_iri(energy_ns)},
            {"@id": self._metric_iri(carbon_ns)},
        ]
        for ref in request.input_refs:
            parts.append({"@id": ref})
        for ref in request.output_refs:
            parts.append({"@id": ref})

        root = {
            "@id": crate_id,
            "@type": "Dataset",
            "name": f"Workflow run {request.workflow_run_id}",
            "description": (
                "RO-Crate-style CIM package for a workflow reproducibility "
                "scenario. Not a fully validated RO-Crate 1.1 crate."
            ),
            "identifier": request.workflow_run_id,
            "hasPart": parts,
            "publisher": request.publisher or "Research Infrastructure (placeholder)",
        }
        if request.temporal_start or request.temporal_end:
            root["temporalCoverage"] = {
                "start": request.temporal_start,
                "end": request.temporal_end,
            }

        run_entity = {
            "@id": run_id_frag,
            "@type": ["schema:Action", "cim:WorkflowRun"],
            "identifier": request.workflow_run_id,
            "name": f"Run {request.workflow_run_id}",
            "object": {"@id": wf_id_frag},
            "workflow_id": request.workflow_id,
            "workflow_run_id": request.workflow_run_id,
            "workflow_energy_per_run": request.energy_per_run,
            "energy_unit": request.energy_unit,
            "workflow_carbon_per_run": request.carbon_per_run,
            "carbon_unit": request.carbon_unit,
            "execution_duration": request.duration_seconds,
            "duration_unit": "s",
            "input_refs": list(request.input_refs),
            "output_refs": list(request.output_refs),
            "source": request.source,
            "asset": request.asset,
            "resource": request.resource,
        }

        workflow_entity = {
            "@id": wf_id_frag,
            "@type": ["schema:SoftwareApplication", "cim:Workflow"],
            "identifier": request.workflow_id,
            "name": request.workflow_id,
        }

        graph = [
            {
                "@id": metadata_id,
                "@type": "CreativeWork",
                "about": {"@id": crate_id},
                "conformsTo": {"@id": "https://w3id.org/ro/crate/1.1"},
                "description": (
                    "RO-Crate-style metadata. Full RO-Crate 1.1 validation "
                    "is future work."
                ),
            },
            root,
            workflow_entity,
            run_entity,
            energy_metric,
            carbon_metric,
            duration_metric,
        ]

        return {
            "@context": ROCRATE_CONTEXT,
            "@graph": graph,
            "profile": PROFILE_ROCRATE,
            "compliance": compliance_block("rocrate"),
            "cim_payload": {
                "workflow_id": request.workflow_id,
                "workflow_run_id": request.workflow_run_id,
                "workflow_energy_per_run": request.energy_per_run,
                "energy_unit": request.energy_unit,
                "workflow_carbon_per_run": request.carbon_per_run,
                "carbon_unit": request.carbon_unit,
                "execution_duration": request.duration_seconds,
                "input_refs": list(request.input_refs),
                "output_refs": list(request.output_refs),
                "source": request.source,
                "asset": request.asset,
                "resource": request.resource,
                "metric_definitions": [
                    self._metric_dict_from_namespace(energy_ns),
                    self._metric_dict_from_namespace(carbon_ns),
                    self._metric_dict_from_namespace(duration_ns),
                ],
                "standards_mappings": [
                    self._crosswalk_entry_dict(m)
                    for m in (list(std_energy.mappings) + list(std_carbon.mappings))
                ],
                "provenance_records": related_prov or prov_records[:25],
                "kpi_results": list(kpi_results or []),
            },
        }

    # ------------------------------------------------------------------
    # DCAT-style
    # ------------------------------------------------------------------

    def export_dcat_style(
        self,
        request: Optional[DcatExportRequest] = None,
    ) -> Dict[str, Any]:
        """DCAT-style catalogue metadata for metric / reporting datasets."""
        req = request or DcatExportRequest()
        metrics = self._collect_metrics()
        variables = [
            {
                "namespace": m["namespace"],
                "label": m["label"],
                "unit": m["canonical_unit"],
                "quantity_kind": m["quantity_kind"],
            }
            for m in metrics
        ]
        crosswalk = self._collect_crosswalk_rows()
        title = req.title or "GreenDIGIT CIM metric catalogue"
        description = req.description or (
            "Registry-driven Common Information Model metric definitions, "
            "standards mappings, and reporting variables."
        )
        publisher = req.publisher or "Research Infrastructure (placeholder)"
        access = req.access_endpoint or "https://example.org/cim/api (placeholder)"
        dataset_id = "cim:dataset/metric-catalogue"
        dist_json = "cim:distribution/metric-catalogue.json"
        dist_csv = "cim:distribution/metric-catalogue.csv"

        dataset = {
            "@id": dataset_id,
            "@type": "dcat:Dataset",
            "dct:title": title,
            "dct:description": description,
            "dcat:keyword": sorted({m["domain"] for m in metrics if m.get("domain")}),
            "dcat:theme": variables,
            "dct:temporal": {
                "start": req.temporal_start,
                "end": req.temporal_end,
            },
            "dcat:distribution": [
                {
                    "@id": dist_json,
                    "@type": "dcat:Distribution",
                    "dct:title": "CIM metric catalogue (JSON)",
                    "dcat:mediaType": "application/json",
                    "dcat:accessURL": access,
                },
                {
                    "@id": dist_csv,
                    "@type": "dcat:Distribution",
                    "dct:title": "CIM metric catalogue (CSV)",
                    "dcat:mediaType": "text/csv",
                    "dcat:accessURL": access,
                },
            ],
            "cim:standardsMappings": crosswalk,
        }

        catalog = {
            "@context": {
                "dcat": "http://www.w3.org/ns/dcat#",
                "dct": "http://purl.org/dc/terms/",
                "foaf": "http://xmlns.com/foaf/0.1/",
                "cim": "https://example.org/greendigit/cim#",
            },
            "@id": "cim:catalog",
            "@type": "dcat:Catalog",
            "dct:title": title,
            "dct:description": description,
            "dct:publisher": {
                "@type": "foaf:Agent",
                "foaf:name": publisher,
            },
            "dcat:dataset": [dataset],
            "dcat:service": {
                "@type": "dcat:DataService",
                "dcat:endpointURL": access,
                "dct:title": "CIM registry API (placeholder)",
            },
            "profile": PROFILE_DCAT,
            "compliance": compliance_block("dcat"),
        }
        return catalog

    # ------------------------------------------------------------------
    # Standards crosswalk
    # ------------------------------------------------------------------

    def export_standards_crosswalk(self) -> Dict[str, Any]:
        rows = self._collect_crosswalk_rows()
        return {
            "format": "standards_crosswalk",
            "profile": PROFILE_CROSSWALK,
            "compliance": compliance_block("standards_crosswalk"),
            "mappings": rows,
        }

    # ------------------------------------------------------------------
    # Evidence readiness
    # ------------------------------------------------------------------

    def export_evidence_readiness(
        self,
        metric_namespace: Optional[str] = None,
        *,
        available_evidence: Optional[List[str]] = None,
        lifecycle_stage: Optional[str] = None,
        reporting_purpose: Optional[str] = None,
    ) -> Dict[str, Any]:
        ns = metric_namespace or "cim:energy.efficiency.pue"
        lookup = self._evidence.get_requirements_for_metric(
            ns,
            lifecycle_stage=lifecycle_stage,
            reporting_purpose=reporting_purpose,
        )
        required = [
            {
                "id": r.id,
                "evidence_type": r.evidence_type,
                "requirement_level": r.requirement_level,
                "standard_code": r.standard_code,
                "description": r.description,
                "boundary": r.boundary,
                "reporting_period": r.reporting_period,
                "aggregation_method": r.aggregation_method,
            }
            for r in lookup.requirements
        ]
        available = list(available_evidence or [])
        required_keys = [
            (r.get("description") or r.get("evidence_type") or "").strip()
            for r in required
        ]
        missing = [
            key
            for key in required_keys
            if key and not any(key.lower() in a.lower() or a.lower() in key.lower() for a in available)
        ]
        mandatory = [
            r
            for r in required
            if (r.get("requirement_level") or "").lower() in {"mandatory", "required"}
        ]
        if not required:
            readiness = "not_applicable"
        elif available_evidence is None:
            # Fulfillment is not persisted; requirements are declared only.
            readiness = "declared" if not mandatory else "incomplete"
        else:
            mandatory_keys = [
                (r.get("description") or r.get("evidence_type") or "").strip()
                for r in mandatory
            ]
            mandatory_missing = [
                k
                for k in mandatory_keys
                if k
                and not any(
                    k.lower() in a.lower() or a.lower() in k.lower() for a in available
                )
            ]
            readiness = "ready" if not mandatory_missing else "incomplete"

        lc = self._lifecycle.get_links_for_metric(ns)
        stages = list(lc.stages) if lc is not None else []
        reporting = {
            "reporting_purpose": reporting_purpose,
            "lifecycle_stage": lifecycle_stage,
            "boundaries": sorted(
                {r.get("boundary") for r in required if r.get("boundary")}
            ),
            "reporting_periods": sorted(
                {
                    r.get("reporting_period")
                    for r in required
                    if r.get("reporting_period")
                }
            ),
        }
        return {
            "format": "evidence_readiness",
            "profile": PROFILE_EVIDENCE,
            "compliance": compliance_block("evidence_readiness"),
            "reportable_metric": ns,
            "required_evidence": required,
            "available_evidence": available,
            "missing_evidence": missing,
            "readiness_status": readiness,
            "lifecycle_context": stages,
            "reporting_context": reporting,
        }

    # ------------------------------------------------------------------
    # Provenance
    # ------------------------------------------------------------------

    def export_provenance(
        self,
        *,
        entity_type: Optional[str] = None,
        entity_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        records = self._collect_provenance_records(
            entity_type=entity_type, entity_id=entity_id
        )
        return {
            "format": "provenance",
            "profile": PROFILE_PROVENANCE,
            "compliance": compliance_block("provenance"),
            "entity_type": entity_type,
            "entity_id": entity_id,
            "records": records,
        }

    # ------------------------------------------------------------------
    # Collectors
    # ------------------------------------------------------------------

    def _collect_metrics(
        self, *, include_candidates: bool = True
    ) -> List[Dict[str, Any]]:
        if self._session is None:
            return []
        from cloud_metrics.models.cim_registry import CimMetricDefinition

        rows = (
            self._session.query(CimMetricDefinition)
            .order_by(CimMetricDefinition.namespace.asc())
            .all()
        )
        out: List[Dict[str, Any]] = []
        for row in rows:
            status = _status_of(row)
            if not include_candidates and status in CANDIDATE_STATUSES:
                continue
            qk = getattr(row, "quantity_kind", None)
            unit = getattr(row, "canonical_unit", None)
            out.append(
                {
                    "id": row.id,
                    "namespace": row.namespace,
                    "label": row.label,
                    "description": row.description,
                    "domain": row.domain,
                    "category": row.category,
                    "subcategory": row.subcategory,
                    "quantity_kind": qk.name if qk is not None else None,
                    "canonical_unit": unit.symbol if unit is not None else None,
                    "metric_type": row.metric_type,
                    "status": status,
                    "review_status": _review_of(row),
                    "version": row.version,
                }
            )
        return out

    def _collect_mappings(self) -> List[Dict[str, Any]]:
        if self._session is None:
            return []
        from cloud_metrics.models.cim_registry import CimMetricMapping

        rows = self._session.query(CimMetricMapping).order_by(CimMetricMapping.id).all()
        out: List[Dict[str, Any]] = []
        for row in rows:
            metric = getattr(row, "metric", None)
            standard = getattr(row, "standard", None)
            term = getattr(row, "standard_term", None)
            out.append(
                {
                    "id": row.id,
                    "source_key": row.source_key,
                    "cim_namespace": metric.namespace if metric is not None else None,
                    "relation_type": row.relation_type,
                    "confidence_score": row.confidence_score,
                    "status": _status_of(row),
                    "review_status": _review_of(row),
                    "origin": row.origin,
                    "rationale": row.rationale,
                    "standard_code": standard.code if standard is not None else None,
                    "standard_term": (
                        (term.term_label or term.term_code) if term is not None else None
                    ),
                }
            )
        return out

    def _collect_crosswalk_rows(self) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        if self._session is None:
            return rows
        from cloud_metrics.models.cim_registry import (
            CimMetricDefinition,
            CimMetricMapping,
            CimStandard,
            CimStandardTerm,
        )

        q = (
            self._session.query(
                CimMetricMapping, CimMetricDefinition, CimStandard, CimStandardTerm
            )
            .join(CimMetricDefinition, CimMetricMapping.metric_id == CimMetricDefinition.id)
            .join(CimStandard, CimMetricMapping.standard_id == CimStandard.id)
            .outerjoin(
                CimStandardTerm,
                CimMetricMapping.standard_term_id == CimStandardTerm.id,
            )
            .filter(CimMetricMapping.standard_id.isnot(None))
            .order_by(CimMetricDefinition.namespace.asc(), CimStandard.code.asc())
        )
        for map_row, metric, standard, term in q.all():
            rows.append(
                {
                    "cim_namespace": metric.namespace,
                    "standard": standard.code,
                    "standard_term": (
                        (term.term_label or term.term_code) if term is not None else None
                    ),
                    "relation_type": map_row.relation_type,
                    "confidence_score": map_row.confidence_score,
                    "review_status": _review_of(map_row),
                    "notes": map_row.rationale or map_row.notes,
                    "status": _status_of(map_row),
                    "mapping_id": map_row.id,
                }
            )
        return rows

    def _collect_lifecycle_links(self) -> List[Dict[str, Any]]:
        if self._session is None:
            return []
        from cloud_metrics.models.cim_registry import (
            CimLifecycleStage,
            CimMetricDefinition,
            CimMetricLifecycleLink,
        )

        q = (
            self._session.query(
                CimMetricLifecycleLink, CimMetricDefinition, CimLifecycleStage
            )
            .join(
                CimMetricDefinition,
                CimMetricLifecycleLink.metric_id == CimMetricDefinition.id,
            )
            .join(
                CimLifecycleStage,
                CimMetricLifecycleLink.lifecycle_stage_id == CimLifecycleStage.id,
            )
            .order_by(CimMetricDefinition.namespace.asc(), CimLifecycleStage.sequence.asc())
        )
        out: List[Dict[str, Any]] = []
        for link, metric, stage in q.all():
            out.append(
                {
                    "cim_namespace": metric.namespace,
                    "stage_key": stage.stage_key,
                    "stage_label": stage.label or stage.name,
                    "relevance": link.relevance,
                    "status": _status_of(link),
                    "review_status": _review_of(link),
                }
            )
        return out

    def _collect_evidence_requirements(self) -> List[Dict[str, Any]]:
        if self._session is None:
            return []
        from cloud_metrics.models.cim_registry import (
            CimEvidenceRequirement,
            CimMetricDefinition,
            CimStandard,
        )

        q = (
            self._session.query(
                CimEvidenceRequirement, CimMetricDefinition, CimStandard
            )
            .join(
                CimMetricDefinition,
                CimEvidenceRequirement.metric_id == CimMetricDefinition.id,
            )
            .join(CimStandard, CimEvidenceRequirement.standard_id == CimStandard.id)
            .order_by(CimMetricDefinition.namespace.asc())
        )
        out: List[Dict[str, Any]] = []
        for req, metric, standard in q.all():
            out.append(
                {
                    "metric_namespace": metric.namespace,
                    "standard_code": standard.code,
                    "evidence_type": req.evidence_type,
                    "requirement_level": req.requirement_level,
                    "reporting_period": req.reporting_period,
                    "aggregation_method": req.aggregation_method,
                    "boundary": req.boundary,
                    "description": req.description,
                    "status": _status_of(req),
                    "review_status": _review_of(req),
                }
            )
        return out

    def _collect_provenance_records(
        self,
        *,
        entity_type: Optional[str] = None,
        entity_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        if self._session is None:
            return []
        from cloud_metrics.models.cim_registry import CimProvenanceRecord

        q = self._session.query(CimProvenanceRecord)
        if entity_type:
            q = q.filter(CimProvenanceRecord.entity_type == entity_type)
        if entity_id is not None:
            q = q.filter(CimProvenanceRecord.entity_id == entity_id)
        rows = q.order_by(CimProvenanceRecord.id.asc()).all()
        out: List[Dict[str, Any]] = []
        for row in rows:
            timestamp = row.started_at or row.created_at or utcnow()
            out.append(
                {
                    "id": row.id,
                    "entity_type": row.entity_type,
                    "entity_id": row.entity_id,
                    "activity": row.activity,
                    "agent": row.agent,
                    "inputs": dict(row.inputs or {}),
                    "outputs": dict(row.outputs or {}),
                    "timestamp": isoformat(timestamp),
                    "started_at": isoformat(row.started_at),
                    "ended_at": isoformat(row.ended_at),
                    "status": _status_of(row, "approved"),
                    "notes": row.notes,
                    "method": row.method,
                    "prov_uri": row.prov_uri,
                }
            )
        return out

    def _collect_extensions(self) -> List[Dict[str, Any]]:
        entries = self._extension.list_entries()
        return [
            {
                "id": e.id,
                "metric_namespace": e.metric_namespace,
                "raw_metric_name": e.raw_metric_name,
                "status": (e.status or "candidate").lower(),
                "review_status": (e.review_status or "under_review").lower(),
                "proposed_standard": e.proposed_standard,
                "justification": e.justification,
                "confidence_score": e.confidence_score,
            }
            for e in entries
        ]

    def _get_metric_row(self, namespace: str):
        if self._session is None or not namespace:
            return None
        from cloud_metrics.models.cim_registry import CimMetricDefinition

        return (
            self._session.query(CimMetricDefinition)
            .filter_by(namespace=namespace)
            .first()
        )

    def _metric_dict_from_namespace(self, namespace: str) -> Optional[Dict[str, Any]]:
        for m in self._collect_metrics():
            if m["namespace"] == namespace:
                return m
        return {"namespace": namespace, "status": "unknown"}

    @staticmethod
    def _crosswalk_entry_dict(m: Any) -> Dict[str, Any]:
        return {
            "cim_namespace": m.metric_namespace,
            "standard": m.standard_code,
            "standard_term": m.standard_term or m.standard_term_code,
            "relation_type": m.relation_type,
            "confidence_score": m.confidence_score,
            "review_status": m.review_status,
            "notes": m.notes,
            "status": m.status,
        }


CimExportService = ExportService
InteroperabilityExportService = ExportService


def get_export_service(session: Optional[Session] = None) -> ExportService:
    return ExportService(session=session)
