# Export Layer

> **Milestone 15** · Registry-driven export and interoperability

## Purpose

`ExportService` (`cloud_metrics/registry/export/`) serialises CIM registry data for reporting, reproducibility, and research packaging. It is **read-only**. It does not replace the internal registry model, does not mutate `cim_*` tables, and does not rewrite candidate status as approved.

Aliases: `CimExportService`, `InteroperabilityExportService`.  
Factory: `get_export_service(session)`.

## Formats

| Format | Status | Profile label |
|--------|--------|----------------|
| JSON | Implemented | `cim-registry-json` |
| CSV | Implemented | `cim-registry-csv` |
| JSON-LD | Partial | `cim-jsonld-partial` |
| RO-Crate-style | Partial | `ro-crate-style` |
| DCAT-style | Partial | `dcat-style` |
| Standards crosswalk | Implemented | `cim-standards-crosswalk` |
| Evidence readiness | Implemented (requirements; fulfillment optional) | `cim-evidence-readiness` |
| Provenance | Implemented (PROV-O-like) | `prov-o-like` |

Every payload includes a `compliance` object: `status`, `profile`, `full_standards_compliance` (always `false` for semantic profiles), and notes.

## Methods

| Method | Output |
|--------|--------|
| `export_json()` | Metric definitions, mappings, standards mappings, lifecycle mappings, evidence requirements, provenance, extension candidates, optional KPI results |
| `export_csv(dataset)` | `metrics` / `mappings` / `standards` / `evidence` / `extensions` |
| `export_jsonld(namespace)` | Lightweight JSON-LD entity for a metric |
| `export_rocrate_style(WorkflowRunExportRequest)` | RO-Crate-style workflow package |
| `export_dcat_style(DcatExportRequest)` | DCAT-style catalogue |
| `export_standards_crosswalk()` | CIM ↔ standard rows with relation type + review status |
| `export_evidence_readiness(namespace)` | Required / available / missing evidence |
| `export_provenance(entity_type, entity_id)` | Provenance event chain |

## Governance

- Candidate / draft / under_review metrics keep their stored `status` and `review_status`.
- Approved standards mappings are **not** attached to non-approved metrics in JSON-LD (same policy as `StandardsRegistryService`).
- Mapping and crosswalk CSVs include `relation_type` and `review_status` as stored.
- `exactMatch` appears only when a curated seed or reviewed row exists.

## Callers

- CLI: `python -m cloud_metrics.scripts.export_cim <format> …`
- API: `/api/v1/cim-export/*`
- Tests / services: `get_export_service(session)`

Ingestion, orchestrator, KPI calculation, and admin review are unchanged.

## Related docs

- [JSON_AND_CSV_EXPORTS.md](JSON_AND_CSV_EXPORTS.md)
- [JSONLD_EXPORT_MODEL.md](JSONLD_EXPORT_MODEL.md)
- [ROCRATE_EXPORT_MODEL.md](ROCRATE_EXPORT_MODEL.md)
- [DCAT_EXPORT_MODEL.md](DCAT_EXPORT_MODEL.md)
- [STANDARDS_CROSSWALK_EXPORT.md](STANDARDS_CROSSWALK_EXPORT.md)
- [PROVENANCE_EXPORT_MODEL.md](PROVENANCE_EXPORT_MODEL.md)
- [LEGACY_EXPORT_HANDLING.md](LEGACY_EXPORT_HANDLING.md)
