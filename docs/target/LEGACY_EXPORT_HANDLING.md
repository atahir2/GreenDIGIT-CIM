# Legacy Export Handling

> **Milestone 15** · What existed before the registry export layer

## Summary

Before Milestone 15 the CIM produced **partner JSON files** and a **mapping JSON cache**. Those paths remain. They are **not** registry interoperability exports (no JSON-LD, CSV catalogues, RO-Crate-style packages, DCAT-style catalogues, evidence readiness, or provenance chains).

## What existed

| Area | Behaviour |
|------|-----------|
| Partner metrics JSON | `cloud_metrics/exporters/external_json.py` → `write_external_metrics_json()` writes `{metadata, metrics}` to `cloud_metrics/data/exports/{basename}_unified.json`. Called from `unified_ingestion.py` and `streamlit_uploader.py`. |
| GD key helper | `unified_to_gd()` converts internal unified keys to `gd.*` form (currently unused in the live write path; conversion is commented out). |
| Mapping JSON rebuild | `cloud_metrics/exporters/rebuild_mapping_json.py` → `rebuild_mapping()` dumps **approved** `CimMapping` (legacy table) rows to `cloud_metrics/data/metric_mapping.json`. |
| Mapping sync export | `cloud_metrics.utils.mapping_sync.export_registry_to_json()` merges legacy `MetricMapping` + `MetricDefinition.sources` into the runtime mapping JSON. |
| Admin panel | “Rebuild mapping JSON” button calls `rebuild_mapping()`. No CIM registry export UI. |
| Dashboard downloads | Streamlit uploader reports the partner JSON path. No CSV/JSON-LD/RO-Crate/DCAT download. |
| Report exports | No dedicated reporting-package exporter. KPI results (Milestone 13) are API/CLI JSON only. |
| JSON-LD / schema.org | Not implemented. SCHEMA-ORG is a **seeded standard catalogue** entry with `contextualMatch` on workflow energy only. |
| RO-Crate | Seeded standard `RO-CRATE` + `contextualMatch` on `cim:workflow.energy.per_run` + a recommended evidence requirement. No crate writer. |
| DCAT | Seeded standard `DCAT` in the catalogue. No catalogue metadata exporter. |
| RDF / Turtle | Not implemented (still future work). |
| Export APIs | `GET /api/v1/export/json` and `/rdf` were listed as **missing** in early gap analysis. Runtime APIs were `/metrics`, `/query`, `/api/v1/registry`, `/api/v1/cim-review`, `/api/v1/cim-kpi`. |

## What it did **not** do

- Export `cim_metric_definitions`, `cim_metric_mappings`, lifecycle links, evidence requirements, extension candidates, or `cim_provenance_records`
- Include **relation type** and **review status** on mapping / standards extracts
- Preserve candidate status honestly in an interoperability payload
- Package a workflow run (energy, carbon, duration, provenance) for research reuse
- Emit DCAT-style dataset / distribution metadata

## Compatibility rule (Milestone 15)

Legacy partner JSON and mapping-cache rebuild are **preserved**. New exports live under `cloud_metrics/registry/export/` and `/api/v1/cim-export/*`. They read CIM registries only; they do not replace `external_json.py` or `rebuild_mapping_json.py`.
