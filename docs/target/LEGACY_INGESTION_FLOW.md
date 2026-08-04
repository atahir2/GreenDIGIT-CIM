# Legacy Ingestion Flow

> **Milestone 7** · Baseline documentation of current ingestion entry points before registry-orchestrated wiring

This document describes the **existing** ingestion paths as of Milestone 6 (approved). Milestone 7 adds a registry orchestrator on **one** path (`unified_ingestion`) without removing these flows.

---

## Entry points

| Path | Module | Entry function | Notes |
|------|--------|----------------|-------|
| File upload (unified) | `cloud_metrics/ingestion/unified_ingestion.py` | `ingest_from_file()` | JSON/XML/CSV/YAML/TXT via parsers |
| Real-time / API dict | `cloud_metrics/ingestion/realtime_ingestor.py` | `ingest_from_api()` | Used by AWS/GCP helpers |
| AWS sample | `cloud_metrics/ingestion/aws.py` | `ingest_aws_metrics()` | Calls `ingest_from_api` |
| GCP sample | `cloud_metrics/ingestion/gcp.py` | `ingest_gcp_metrics()` | Calls `ingest_from_api` |
| HTTP triggers | `cloud_metrics/api/metrics.py` | `/aws`, `/gcp` | Thin FastAPI wrappers |
| Streamlit uploader | `cloud_metrics/scripts/streamlit_uploader.py` | UI upload | Uses `load_any_file` + `process_metric_sample` |
| Core per-metric | `cloud_metrics/ingestion/automated_mapper.py` | `process_metric_sample()` | Shared classify → persist |
| Partner / any-file | `cloud_metrics/utils/ingest_any.py` | `load_any_file()` | Parser only (no orchestrator yet) |
| Structured parser | `cloud_metrics/parsers/structured_parser.py` | `parse_structured_file()` | JSON/YAML/CSV/XML → flat numerics |
| Unstructured parser | `cloud_metrics/parsers/unstructured_parser.py` | `parse_unstructured_text()` | TXT → metrics |
| File parse + JSON map | `cloud_metrics/mapping/namespace_mapper_core.py` | `parse_and_extract_file_metrics()` | Parse then `map_raw_to_unified` |

---

## Canonical legacy flow (file upload)

```
file path
  → ingest_from_file()
  → validate extension (.json/.xml/.csv/.yaml/.txt)
  → insert_datacenter()
  → parse_and_extract_file_metrics()
       → parse_structured_file() | parse_unstructured_text()
       → map_raw_to_unified()  (side map; unified_ingestion uses raw dict)
  → for each raw_key, value:
       → process_metric_sample()
            → datacenter / legacy Asset / Source lookup
            → classify_metric() (ensemble → CimMapping → alias → rules)
            → ensure_gd_namespace()
            → optional auto_learn_mapping()
            → legacy Unit conversion (MetricDefinition + Unit)
            → rule_registry validate_metric_sample()
            → register_mapping / insert_mapped_metric / insert_metric_sample
            → provenance record_activity()
            → sync_metric_mapping() JSON
  → write_external_metrics_json()
  → write_mapped_metrics() (Influx)
  → insert_file_upload_log()
  → insert_metric_definition() per unified key
```

---

## API / real-time flow

```
metric_data dict
  → ingest_from_api()
  → for each raw_key, value: process_metric_sample()
  → write_mapped_metrics()
  → insert_file_upload_log() (API-* filename)
  → insert_metric_definition()
```

AWS/GCP helpers build a sample dict and call `ingest_from_api`.

---

## Classification stack (inside `process_metric_sample`)

1. `ensemble_classifier.classify_metric` — legacy `resolve_mapping(CimMapping)` first, then semantic / alias / rules / embed
2. Fallback namespace when uncategorized (`fallback_namespace_from_raw`)
3. `ensure_gd_namespace` → `gd.<cat>.<sub>.<key>`
4. Optional `auto_learn_mapping` when confidence ≥ 0.85

Registry-first `resolve_raw_metric()` (Milestones 4–6) exists but was **opt-in** and not wired into these callers before Milestone 7.

---

## Storage sinks (unchanged by Milestone 7 design)

* PostgreSQL: metric samples, definitions, upload logs, legacy Asset/Source, CimMapping
* InfluxDB: `write_mapped_metrics`
* External JSON export: `write_external_metrics_json`
* JSON mapping file: `sync_metric_mapping`

---

## Milestone 7 change surface

| Caller | Orchestrator? |
|--------|---------------|
| `unified_ingestion.ingest_from_file` | **Yes** (default on; opt-out via flag) |
| `realtime_ingestor.ingest_from_api` | No (legacy) |
| `streamlit_uploader` | No (legacy) |
| Direct `process_metric_sample(...)` | No unless `use_registry_orchestrator=True` |

Legacy fallback inside the Mapping Registry remains available. Old ingestion functions are not removed.
