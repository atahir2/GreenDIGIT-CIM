"""Export / interoperability types (Milestone 15).

These dataclasses describe *export payloads*. They do not replace CIM
registry models. Semantic profiles (JSON-LD, RO-Crate, DCAT, PROV-O)
are labelled implemented vs partial vs future — never claimed as full
standards compliance.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Compliance labels (honest, not marketing)
# ---------------------------------------------------------------------------

PROFILE_JSON = "cim-registry-json"
PROFILE_CSV = "cim-registry-csv"
PROFILE_JSONLD = "cim-jsonld-partial"
PROFILE_ROCRATE = "ro-crate-style"
PROFILE_DCAT = "dcat-style"
PROFILE_CROSSWALK = "cim-standards-crosswalk"
PROFILE_EVIDENCE = "cim-evidence-readiness"
PROFILE_PROVENANCE = "prov-o-like"

COMPLIANCE: Dict[str, Dict[str, Any]] = {
    "json": {
        "status": "implemented",
        "profile": PROFILE_JSON,
        "full_standards_compliance": False,
        "notes": "Native CIM JSON dump of registry tables and optional KPI results.",
    },
    "csv": {
        "status": "implemented",
        "profile": PROFILE_CSV,
        "full_standards_compliance": False,
        "notes": "Tabular extracts; encodings are CIM field names, not a published CSV dialect.",
    },
    "jsonld": {
        "status": "partial",
        "profile": PROFILE_JSONLD,
        "full_standards_compliance": False,
        "notes": (
            "Lightweight JSON-LD with schema.org / QUDT / PROV-O-like terms where "
            "safe. Not a complete ontology mapping or SHACL-validated graph."
        ),
    },
    "rocrate": {
        "status": "partial",
        "profile": PROFILE_ROCRATE,
        "full_standards_compliance": False,
        "notes": (
            "RO-Crate-style / RO-Crate-ready metadata package. Uses the RO-Crate "
            "1.1 context URL where convenient but is not a fully validated crate "
            "(no payload files, no RO-Crate validator run)."
        ),
    },
    "dcat": {
        "status": "partial",
        "profile": PROFILE_DCAT,
        "full_standards_compliance": False,
        "notes": (
            "DCAT-style catalogue metadata. Not DCAT-AP / DCAT-US validated. "
            "Publisher and access endpoints are placeholders unless supplied."
        ),
    },
    "standards_crosswalk": {
        "status": "implemented",
        "profile": PROFILE_CROSSWALK,
        "full_standards_compliance": False,
        "notes": (
            "Exports seeded relation_type and review_status. exactMatch is only "
            "present when a curated seed/review row exists."
        ),
    },
    "evidence_readiness": {
        "status": "implemented",
        "profile": PROFILE_EVIDENCE,
        "full_standards_compliance": False,
        "notes": (
            "Required evidence comes from the Evidence Registry. Available/"
            "missing evidence is computed only when the caller supplies "
            "fulfillment; the registry does not yet persist fulfillment."
        ),
    },
    "provenance": {
        "status": "implemented",
        "profile": PROFILE_PROVENANCE,
        "full_standards_compliance": False,
        "notes": (
            "PROV-O-like records (entity, activity, agent, inputs, outputs). "
            "Not a complete PROV-O RDF serialization."
        ),
    },
}

# Safe JSON-LD context — only well-known vocabularies, no invented IRIs
# claimed as official GreenDIGIT ontology.
JSONLD_CONTEXT: Dict[str, Any] = {
    "schema": "https://schema.org/",
    "cim": "https://example.org/greendigit/cim#",
    "qudt": "http://qudt.org/schema/qudt/",
    "quantitykind": "http://qudt.org/vocab/quantitykind/",
    "prov": "http://www.w3.org/ns/prov#",
    "skos": "http://www.w3.org/2004/02/skos/core#",
    "dcat": "http://www.w3.org/ns/dcat#",
    "dct": "http://purl.org/dc/terms/",
    "foaf": "http://xmlns.com/foaf/0.1/",
    "name": "schema:name",
    "description": "schema:description",
    "identifier": "schema:identifier",
    "unitCode": "schema:unitCode",
    "dateCreated": "schema:dateCreated",
}

ROCRATE_CONTEXT = "https://w3id.org/ro/crate/1.1/context"

# SKOS-like mapping for relation types that have a close SKOS analogue.
# CIM-specific relations stay as cim:* predicates (not overclaimed as SKOS).
RELATION_TO_JSONLD: Dict[str, str] = {
    "exactMatch": "skos:exactMatch",
    "closeMatch": "skos:closeMatch",
    "broadMatch": "skos:broadMatch",
    "narrowMatch": "skos:narrowMatch",
    "relatedMatch": "skos:relatedMatch",
    "inputToKPI": "cim:inputToKPI",
    "derivedFrom": "cim:derivedFrom",
    "contextualMatch": "cim:contextualMatch",
    "extensionMetric": "cim:extensionMetric",
    "noMatch": "cim:noMatch",
    "underReview": "cim:underReview",
}

APPROVED_STATUSES = frozenset({"approved", "active"})
CANDIDATE_STATUSES = frozenset(
    {"candidate", "draft", "pending", "under_review", "rejected", "proposed"}
)

CSV_DATASETS = (
    "metrics",
    "mappings",
    "standards",
    "evidence",
    "extensions",
)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def isoformat(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def compliance_block(key: str, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    block = dict(COMPLIANCE[key])
    block["generated_at"] = isoformat(utcnow())
    if extra:
        block.update(extra)
    return block


@dataclass
class WorkflowRunExportRequest:
    """Inputs for an RO-Crate-style workflow reproducibility package."""

    workflow_id: str
    workflow_run_id: str
    energy_per_run: Optional[float] = None
    energy_unit: str = "kWh"
    carbon_per_run: Optional[float] = None
    carbon_unit: str = "kgCO2e"
    duration_seconds: Optional[float] = None
    input_refs: List[str] = field(default_factory=list)
    output_refs: List[str] = field(default_factory=list)
    source: Optional[str] = None
    asset: Optional[str] = None
    resource: Optional[str] = None
    publisher: Optional[str] = None
    temporal_start: Optional[str] = None
    temporal_end: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DcatExportRequest:
    """Optional overrides for DCAT-style catalogue metadata."""

    title: Optional[str] = None
    description: Optional[str] = None
    publisher: Optional[str] = None
    access_endpoint: Optional[str] = None
    dataset_kind: str = "metric_catalogue"
    temporal_start: Optional[str] = None
    temporal_end: Optional[str] = None


@dataclass
class ExportManifest:
    """Top-level envelope shared by JSON-family exports."""

    format: str
    profile: str
    compliance: Dict[str, Any] = field(default_factory=dict)
    generated_at: Optional[str] = None
    payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "format": self.format,
            "profile": self.profile,
            "compliance": dict(self.compliance),
            "generated_at": self.generated_at or isoformat(utcnow()),
            **self.payload,
        }
