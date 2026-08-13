# Standards Crosswalk Export

> **Milestone 15**

## Purpose

Tabular / JSON extract of CIM metric ↔ external standard mappings **as stored**, including relation type and review status. Does not invent `exactMatch`.

## Fields

| Field | Source |
|-------|--------|
| `cim_namespace` | Linked `cim_metric_definitions.namespace` |
| `standard` | `cim_standards.code` |
| `standard_term` | Linked term label/code when present |
| `relation_type` | `cim_metric_mappings.relation_type` |
| `confidence_score` | mapping confidence |
| `review_status` | mapping `review_status` |
| `notes` | rationale / notes |
| `status` | mapping governance `status` |

Rows are mappings with `standard_id` set (seeded crosswalk plus any later reviewed standard links).

## Conservative claims

- PUE ↔ ISO/IEC 30134 and EN 50600 may appear as `exactMatch` because they are **seeded**.
- Workflow energy ↔ RO-CRATE / PROV-O / SCHEMA-ORG / QUDT appear as `contextualMatch` only.
- Candidate metrics do not inherit approved identity claims in JSON-LD; the crosswalk export still lists **mapping rows** with their own status (a candidate mapping stays `candidate`).

See [STANDARDS_ALIGNMENT_POLICY.md](STANDARDS_ALIGNMENT_POLICY.md).

## API / CLI

```text
GET /api/v1/cim-export/standards-crosswalk
python -m cloud_metrics.scripts.export_cim crosswalk --out crosswalk.json
python -m cloud_metrics.scripts.export_cim csv standards --out crosswalk.csv
```
