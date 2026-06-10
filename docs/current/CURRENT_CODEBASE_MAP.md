# Current Codebase Map — GreenDIGIT CIM

> **Generated**: 2026-06-10 · **Scope**: Full project audit (read-only)

---

## Root Directory

```
GreenDIGIT_CIM_testing_v1/
├── .env                          # Live environment config (DB, Influx, CORS, mapping path)
├── .env.sample                   # Template for new developers
├── .flake8                       # Flake8 lint config
├── .github/workflows/            # CI pipeline (GitHub Actions)
├── README.md                     # Minimal project readme
├── __init__.py                   # Root package marker (empty)
├── gd-sql.sql                    # Ad-hoc SQL query (metric_definitions ↔ standards)
├── pyproject.toml                # Build config + dependencies (setuptools)
├── pytest.ini                    # Pytest config
├── requirements.txt              # Pinned dependencies
├── setup.py                      # Legacy setuptools entry
├── influxdb2-2.7.11-windows.zip  # Bundled InfluxDB binary (48 MB)
│
├── cloud_metrics/                # ★ Main Python package
├── sample_data/                  # Test input files (multi-format)
├── output/                       # Runtime output (exported JSON files)
├── sql_scripts/                  # Raw SQL DDL scripts
└── tests/                        # Pytest test suite
```

---

## `cloud_metrics/` — Main Package

### Top-Level

| File | Role |
|------|------|
| `__init__.py` | Package marker (empty) |
| `main.py` | **FastAPI application entry point** — mounts `/metrics` and `/query` routers, exposes `/health` |
| `docker-compose.yml` | Docker services: PostgreSQL 15 + InfluxDB 2.7.11 |
| `setup.cfg` | Setuptools metadata |

---

### `api/` — FastAPI Routers

| File | Role |
|------|------|
| `__init__.py` | Package marker |
| `metrics.py` | `GET /metrics/aws` and `GET /metrics/gcp` — triggers stub cloud ingestion |
| `query.py` | `GET /query/` — proxies Flux queries to InfluxDB with tag filters |

---

### `classifiers/` — Metric Classification Engine

| File | Role |
|------|------|
| `__init__.py` | Package marker |
| `alias_classifier.py` | **Fuzzy alias matching** via RapidFuzz (WRatio, cutoff=88). Contains hardcoded `ALIASES` dict mapping `(category, subcategory, short_key)` → list of known raw metric names |
| `ensemble_classifier.py` | **Ensemble classifier** — chains: (1) semantic map → (2) fuzzy alias → (3) token-based rules → (4) sentence-transformer embeddings → (5) fallback "uncategorized" |
| `fallbacks.py` | Last-resort taxonomy generator from raw key tokens. **Note: contains dead code** after early `return` on line 19 |

---

### `ingestion/` — Data Ingestion Pipeline

| File | Role |
|------|------|
| `__init__.py` | Package marker |
| `automated_mapper.py` | **Core ingestion orchestrator** `process_metric_sample()` — classifies a single raw metric, generates namespace, persists to DB + JSON, learns keywords, writes samples. Contains **duplicated** classification logic (rules at L86–130 duplicate `ensemble_classifier.py`) |
| `semantic_classifier.py` | **Standards-based lookup**: 10 hardcoded entries in `STANDARDS_MAP` mapping normalized key suffixes → `(org, domain, category, metric)` |
| `unified_ingestion.py` | **File-based ingestion** `ingest_from_file()` — parses file → classifies each metric → writes InfluxDB + SQL + export JSON. **Hardcodes `datacenter_id=1`** |
| `realtime_ingestor.py` | **API-based ingestion** `ingest_from_api()` — maps dict metrics → writes InfluxDB. **Hardcodes `datacenter_id=1`** |
| `decision.py` | `MappingDecision` frozen dataclass (unified_key, confidence, rationale, unit, tags) |
| `unit_normalizer.py` | `extract_numeric_and_unit()` — regex patterns for %, MB, GB, W |
| `aws.py` | **Stub** AWS ingestion — returns hardcoded `{"CPUUtilization": 12.3, "FreeableMemory": 2048}` |
| `gcp.py` | **Stub** GCP ingestion — returns hardcoded `{"CPU_UsagePercent": 8.9, "MemoryAvailableMB": 1024}` |

---

### `mapping/` — Namespace Mapping

| File | Role |
|------|------|
| `__init__.py` | Package marker |
| `namespace_mapper.py` | `map_raw_to_unified()` — JSON-file-based reverse lookup (raw_key → unified_key). Uses `@lru_cache` |
| `namespace_mapper_core.py` | `parse_and_extract_file_metrics()` — orchestrates file parsing + mapping; `extract_metrics()` for API dicts |
| `metric_mapping.json` | **Runtime mapping file** — `{ "gd.x.y.z": ["raw1", "raw2", ...] }`. Contains datacenter names and raw keys mixed as source entries |

---

### `models/` — SQLAlchemy ORM Models

| File | Model(s) | Table(s) |
|------|----------|----------|
| `__init__.py` | Re-exports all models; configures imports |  |
| `db_models.py` | `Base` (declarative base) | — |
| `datacenter.py` | `Datacenter` | `datacenters` |
| `metric_definition.py` | `MetricDefinition` | `metric_definitions` |
| `metric_sample.py` | `MetricSample` | `metric_samples` |
| `metric_keyword.py` | `MetricKeyword` | `metric_keywords` |
| `metric_mapping.py` | `MetricMapping`, `MappingProposal`, `MappingEvent` | `metric_mappings`, `mapping_proposals`, `mapping_events` |
| `metric_source_map.py` | `MetricSourceMap` | `metric_source_map` |
| `namespace_models.py` | `Category`, `Subcategory` | `categories`, `subcategories` |
| `standard_models.py` | `Standard`, `MetricStandardMap` | `standards`, `metric_standard_map` |
| `upload_log.py` | `FileUploadLog` | `file_upload_logs` |

---

### `registry/` — Namespace & Mapping Registry

| File | Role |
|------|------|
| `__init__.py` | Package marker |
| `namespace_registry.py` | `ensure_gd_namespace()` — auto-creates Category/Subcategory rows in DB; returns `gd.cat.sub.short` string |
| `mapping_registry.py` | `register_mapping()` — writes MetricDefinition + MetricSourceMap + JSON sync; `upsert_keyword()` |

---

### `services/` — Database & External Service Layer

| File | Role |
|------|------|
| `__init__.py` | Package marker |
| `influx_service.py` | InfluxDB client: `write_metrics()`, `write_mapped_metrics()`, `query_metrics()` |
| `insert_datacenter.py` | `insert_datacenter()`, `get_or_create_datacenter_id()` |
| `insert_file_upload_log.py` | `insert_file_upload_log()` |
| `insert_mapped_metric.py` | `insert_mapped_metric()` — upserts MetricDefinition, syncs JSON mapping, attaches standards |
| `insert_metric_definition.py` | `insert_metric_definition()` — simple insert (no upsert merge) |
| `insert_metric_sample.py` | `insert_metric_sample()` — inserts MetricSample + upserts MetricSourceMap |
| `keyword_learning.py` | `learn_keyword()` — writes/updates MetricKeyword rows |
| `namespace_generator.py` | `generate_namespace()` — DB-driven lookup using Standard+Category+Subcategory with alias support |
| `registry_service.py` | `resolve_unified_key()` — looks up approved MetricMapping by raw_key |
| `standards_registry.py` | `ensure_seed_standards()` — seeds 12 standards; `attach_standard()` — rule-based linking of unified keys to standards with confidence scores |

---

### `parsers/` — File Format Parsers

| File | Role |
|------|------|
| `__init__.py` | Package marker |
| `structured_parser.py` | `parse_structured_file()` — handles JSON/JSONL/NDJSON/YAML/CSV/XML → flat `{key: float}` dict |
| `unstructured_parser.py` | `parse_unstructured_text()` — regex extraction from free-form English text (cpu, memory, power, network, temperature) |

---

### `exporters/` — Output Generation

| File | Role |
|------|------|
| `__init__.py` | Package marker |
| `external_json.py` | `write_external_metrics_json()` — exports `{metadata, metrics}` JSON files to `cloud_metrics/data/exports/` |
| `rebuild_mapping_json.py` | `rebuild_mapping()` — rebuilds `metric_mapping.json` from DB (MetricSourceMap → MetricKeyword fallback) |

---

### `utils/` — Shared Utilities

| File | Role |
|------|------|
| `__init__.py` | Package marker |
| `.env` | **Stale** secondary env file (`DATABASE_URL=sqlite:///./test.db`) |
| `config.py` | **Central configuration**: `Settings` (pydantic-settings), `SessionLocal`, `get_mapping_path()`, InfluxDB settings views |
| `debug_config.py` | Debug script — prints env file locations and tests pydantic settings loading |
| `ingest_any.py` | **Universal file loader** `load_any_file()` — supports JSON/YAML/XML/CSV/TXT with 3 extraction strategies (partner-generic, legacy metadata+metrics, deep-scan). Contains its own `PartnerMeta` dataclass |
| `mapping_sync.py` | `sync_metric_mapping()` — atomic read/modify/write of the JSON mapping file; `export_registry_to_json()` |
| `metadata.py` | `parse_partner_metadata()` — legacy metadata parser (expects `{metadata, metrics}` shape). Contains its own `IngestMeta` dataclass |
| `partner_payload.py` | `parse_partner_payload_generic()` — partner payload parser (expects `{site_type, fact, detail}` shape). Contains its own `PartnerMeta` dataclass |
| `unified_key.py` | `to_gd()` — normalizes any dotted key to `gd.cat.sub.short` format |

---

### `scripts/` — CLI & UI Scripts

| File | Role |
|------|------|
| `__init__.py` | Package marker |
| `streamlit_uploader.py` | **Streamlit UI** (493 lines, ~50% commented-out legacy code) — file upload → parse → classify → persist → export |
| `admin_panel.py` | **Streamlit UI** — review unknown/uncategorized metrics, approve mappings, retrofix samples, rebuild JSON |
| `seed_namespace.py` | Seeds taxonomy: `iso`→(performance, storage, network, energy, environment); `jrc`→(environment) |
| `seed_taxonomy_standards.py` | Seeds unified keys, alias keywords, and standards catalog |
| `backfill_standards.py` | Backfills standards linkage for existing metric definitions |
| `create_schema.py` | Runs `Base.metadata.create_all()` to create all tables |
| `rebuild_mapping_json.py` | CLI wrapper for `exporters.rebuild_mapping_json.rebuild_mapping()` |

---

## `tests/` — Test Suite

| File | Tests | Status |
|------|-------|--------|
| `test_api_endpoints.py` | 4 tests: AWS/GCP ingest, query success/failure | Uses monkeypatch; no DB required |
| `test_influx_service.py` | 1 test: write_metrics batching | Monkeypatches write API |
| `test_namespace_mapper.py` | 3 tests: known key mapping, unknown key | **Likely broken** — expects old mapping keys (`CPUUtilization`→`cpu_usage`) |
| `test_sql_service.py` | 1 test: insert + query | **Broken** — imports `cloud_metrics.services.sql_service` which does not exist |

---

## `sql_scripts/` — Raw SQL

| File | Purpose |
|------|---------|
| `create_metric_keywords_table.sql` | DDL for `metric_keywords` table |
| `namespace_schema.sql` | DDL for `standards`, `categories`, `subcategories`, `metric_definitions` |
| `namespace_with_descriptions.sql` | Seed data with descriptions for standards and categories |

---

## `sample_data/` — Test Input Files

| File | Format | Domain |
|------|--------|--------|
| `payload_cloud.json` | Partner JSON (site_type/fact/detail) | Cloud (AWS) |
| `payload_grid.json` | Partner JSON | Grid (INFN-T1) |
| `payload_network.json` | Partner JSON | Network |
| `datacenter_A.json` | Legacy JSON (metadata/metrics) | Generic |
| `datacenter_B.xml` | XML | Generic |
| `datacenter_C.csv` | CSV | Generic |
| `datacenter_D.yaml` | YAML | Generic |
| `datacenter_Z.json` | Simplified JSON | Generic |
| `ifca.json` | Partner JSON | Grid (IFCA) |
| `unstructured_dc_1.txt` | Free-form English text | Generic |
| `unstructured_dc_2.txt` | Free-form English text | Generic |

---

## `output/` — Runtime Output

Contains 32 exported JSON files with naming pattern `{site_id}_{timestamp}.json`. These are output artifacts from previous ingestion runs.

---

## Key Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| FastAPI | ~0.116.1 | REST API framework |
| SQLAlchemy | ~2.0.43 | ORM / PostgreSQL access |
| pydantic / pydantic-settings | ~2.11 / ~2.10 | Config + validation |
| influxdb-client | ~1.49.0 | InfluxDB 2.x time-series writes/queries |
| Streamlit | ~1.48.1 | UI (uploader + admin panel) |
| RapidFuzz | ~3.13.0 | Fuzzy string matching for alias classifier |
| sentence-transformers | ~5.1.0 | Embedding-based classification (optional) |
| PyYAML | ~6.0.2 | YAML parsing |
| python-dotenv | ~1.1.1 | Environment file loading |
