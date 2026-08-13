# JSON and CSV Exports

> **Milestone 15**

## JSON (`export_json`)

Native CIM dump. Not JSON-LD.

| Key | Source |
|-----|--------|
| `metric_definitions` | `cim_metric_definitions` (+ quantity kind name, canonical unit symbol, `status`, `review_status`) |
| `metric_mappings` | `cim_metric_mappings` including `relation_type` and `review_status` |
| `standards_mappings` | mappings with `standard_id` set (crosswalk rows) |
| `lifecycle_mappings` | `cim_metric_lifecycle_links` |
| `evidence_requirements` | `cim_evidence_requirements` |
| `provenance_records` | `cim_provenance_records` |
| `extension_candidates` | `cim_extension_metrics` |
| `kpi_results` | Optional caller-supplied `KpiCalculationResult.to_dict()` list (empty by default) |

`include_candidates=True` (default) keeps candidate metrics in the catalogue with their real status.

## CSV datasets (`export_csv`)

| Dataset aliases | Columns (minimum) |
|-----------------|-------------------|
| `metrics` / `metric_catalogue` | namespace, label, description, domain, category, subcategory, quantity_kind, canonical_unit, metric_type, status, review_status, version |
| `mappings` / `mapping_registry` | source_key, cim_namespace, relation_type, confidence_score, status, review_status, origin, rationale, standard_code, standard_term |
| `standards` / `standards_crosswalk` | cim_namespace, standard, standard_term, relation_type, confidence_score, review_status, notes, status |
| `evidence` / `evidence_readiness` | reportable_metric, required_evidence, available_evidence, missing_evidence, readiness_status, requirement_level, standard_code, lifecycle_context, reporting_context |
| `extensions` / `extension_candidates` | metric_namespace, raw_metric_name, status, review_status, proposed_standard, justification, confidence_score |

CSV is a CIM field extract, not a published tabular standard.

## CLI / API

```text
python -m cloud_metrics.scripts.export_cim json --out registry.json
python -m cloud_metrics.scripts.export_cim csv mappings --out mappings.csv
GET /api/v1/cim-export/json
GET /api/v1/cim-export/csv/{metrics|mappings|standards|evidence|extensions}
```
