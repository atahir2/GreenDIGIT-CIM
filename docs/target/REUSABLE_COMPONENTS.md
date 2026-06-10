# Reusable Components

> **Generated**: 2026-06-10 · **Scope**: Components that can be directly reused or minimally adapted for the target architecture

---

## 1. Fully Reusable (No Changes Needed)

These components are well-written, stable, and fit directly into the target architecture.

### 1.1 Structured Parser

**File**: [structured_parser.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/parsers/structured_parser.py)

**What it does**: Parses JSON/JSONL/NDJSON/YAML/CSV/XML files into flat `{key: float}` dicts.

**Why reusable**:
- Format-agnostic, clean function signatures
- Handles BOM, multi-document YAML, nested JSON flattening
- No dependencies on any CIM-specific logic
- Can be used as-is in any Source Registry connector

**Target location**: `cloud_metrics/parsers/structured_parser.py` (unchanged)

---

### 1.2 Unstructured Parser

**File**: [unstructured_parser.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/parsers/unstructured_parser.py)

**What it does**: Regex extraction of 6 metric types from free-form English text.

**Why reusable**:
- Self-contained, no external dependencies
- Pure function with no side effects
- Extensible pattern set

**Target location**: `cloud_metrics/parsers/unstructured_parser.py` (unchanged)

---

### 1.3 InfluxDB Service

**File**: [influx_service.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/services/influx_service.py)

**What it does**: Lazy-initialized InfluxDB client with write (sync) and query (Flux) capabilities.

**Why reusable**:
- Clean abstraction over influxdb-client
- Handles multiple input formats (dict, 3-tuple, 4-tuple)
- No CIM-specific logic — pure time-series I/O

**Target location**: `cloud_metrics/services/influx_service.py` (unchanged)

---

### 1.4 Configuration System

**File**: [config.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/utils/config.py)

**What it does**: Pydantic-settings based configuration for PostgreSQL, InfluxDB, and application settings.

**Why reusable**:
- Clean separation of concerns
- Environment-variable driven
- `SessionLocal` context manager pattern
- `get_mapping_path()` utility

**Target location**: `cloud_metrics/utils/config.py` (unchanged, extend with new registry settings as needed)

---

### 1.5 Unified Key Normalizer

**File**: [unified_key.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/utils/unified_key.py)

**What it does**: Normalizes any dotted key to `gd.category.subcategory.short_key` format.

**Why reusable**:
- Pure function, no side effects
- Essential for the `gd.*` namespace convention which is retained in the target

**Target location**: `cloud_metrics/utils/unified_key.py` (unchanged)

---

### 1.6 Test: InfluxDB Service

**File**: [test_influx_service.py](file:///z:/GreenDIGIT_CIM_testing_v1/tests/test_influx_service.py)

**Why reusable**: Tests `write_metrics()` with monkeypatched write API. Validates batching and line protocol output.

---

### 1.7 Debug Config Utility

**File**: [debug_config.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/utils/debug_config.py)

**Why reusable**: Dev-only diagnostic tool. No changes needed.

---

## 2. Reusable with Minor Adaptation

These components have the right architecture but need field additions or reference updates.

### 2.1 Standards Registry Service

**File**: [standards_registry.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/services/standards_registry.py)

**What's reusable**:
- `ensure_seed_standards()` — idempotent seeding pattern ✅
- `_guess_standard_codes()` — rule-based standard inference ✅
- `attach_standard()` — confidence-based linking ✅
- Seed data: 12 standards (TGG-PUE, TGG-WUE, GHG, ISO-50001, ASHRAE, IEEE, IETF, SNIA, JRC-CoC) ✅

**Required adaptation**:
- Extend seed data with ~12 additional standards (SAREF, QUDT, PROV-O, etc.)
- Add `vocabulary_type`, `namespace_prefix`, `namespace_uri` to Standard model
- Move `MetricStandardMap` linkage rules into Mapping Registry with relation_type

---

### 2.2 Standard Model

**File**: [standard_models.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/models/standard_models.py)

**What's reusable**:
- `Standard` model — good schema, just needs extension
- `MetricStandardMap` model — correct linkage pattern, needs relation_type

**Required adaptation**:
- Add fields: `vocabulary_type`, `namespace_prefix`, `namespace_uri`, `version`, `domain`, `status`

---

### 2.3 Ensemble Classifier Architecture

**File**: [ensemble_classifier.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/classifiers/ensemble_classifier.py)

**What's reusable**:
- Cascading classifier pattern (try semantic → alias → rules → embeddings → fallback) ✅
- `_tokens()` / `_norm()` tokenization ✅
- `_rule_guess()` token-intersection logic ✅
- `_embed_guess()` sentence-transformer integration ✅
- `ClassificationResult` dataclass ✅

**Required adaptation**:
- Insert Mapping Registry DB lookup as priority 0 (before semantic)
- Add `relation_type` to classification output
- Replace hardcoded alias dict references with Mapping Registry queries

---

### 2.4 Alias Classifier Data

**File**: [alias_classifier.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/classifiers/alias_classifier.py)

**What's reusable**:
- ~80 high-quality alias entries covering energy, network, storage, environment, performance domains ✅
- RapidFuzz integration ✅
- Fuzzy matching function ✅

**Required adaptation**:
- Migrate the 80 alias entries into Mapping Registry seed data as rows with `relation_type=exactMatch` or `closeMatch`
- Keep the RapidFuzz matching function as a classification strategy

---

### 2.5 Metric Definition Model

**File**: [metric_definition.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/models/metric_definition.py)

**What's reusable**:
- `unified_key` (UNIQUE), `tags` (JSON), `sources` (JSON), `created_at` ✅

**Required adaptation**:
- Add: `label`, `description`, `domain`, `quantity_kind`, `canonical_unit`, `metric_type`, `status`, `version`, `updated_at`

---

### 2.6 Metric Sample Model

**File**: [metric_sample.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/models/metric_sample.py)

**What's reusable**:
- Core observation model with rich metadata ✅
- `datacenter_id`, `unified_key`, `raw_key`, `value`, `unit`, `tags`, `captured_at`, `source_file` ✅
- `domain`, `extra_meta` JSONB ✅

**Required adaptation**:
- Replace `datacenter_id` FK with `asset_id` FK (→ Asset Registry)
- Move `ri_id`, `node_id`, `vm_id`, `host`, `site_id` to Asset Registry
- Move `clf_confidence`, `clf_rationale` to Provenance Registry
- Add `source_id` FK (→ Source Registry)

---

### 2.7 Insert Mapped Metric Service

**File**: [insert_mapped_metric.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/services/insert_mapped_metric.py)

**What's reusable**:
- Idempotent upsert logic (case-insensitive lookup, merge sources/tags) ✅
- Standards hook pattern (`attach_standard()` call) ✅
- Robust error handling that doesn't block ingestion ✅

**Required adaptation**:
- Remove `sync_metric_mapping()` call (JSON sync eliminated)
- Update to use expanded MetricDefinition fields

---

### 2.8 Universal File Loader

**File**: [ingest_any.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/utils/ingest_any.py)

**What's reusable**:
- Three-strategy extraction (partner-generic, legacy metadata+metrics, deep-scan) ✅
- Domain detection from payload shape and key names ✅
- `_extract_timestamps()` heuristic ✅
- `_flatten_numeric()` recursive flattening ✅

**Required adaptation**:
- Consolidate PartnerMeta into single class shared with `partner_payload.py`
- Return Source Registry reference alongside parsed data
- Return extracted unit alongside value

---

### 2.9 Partner Payload Parser

**File**: [partner_payload.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/utils/partner_payload.py)

**What's reusable**:
- `_from_partner_generic()` function — handles cloud/grid/network payloads ✅
- Domain-aware extraction (separates fact vs. detail sections) ✅
- Site ID construction logic ✅

**Required adaptation**:
- Merge PartnerMeta with `ingest_any.py` version
- Link site metadata to Asset Registry entries

---

### 2.10 Namespace Registry

**File**: [namespace_registry.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/registry/namespace_registry.py)

**What's reusable**:
- `ensure_gd_namespace()` auto-creation pattern ✅
- Guard against polluting taxonomy with uncategorized/unknown ✅
- Case-insensitive DB lookups ✅

**Required adaptation**:
- Validate against Metric Registry instead of bare taxonomy tables
- Use Metric Registry service for creation

---

### 2.11 Mapping Sync (Atomic Write Pattern)

**File**: [mapping_sync.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/utils/mapping_sync.py)

**What's reusable**:
- Atomic file write pattern (temp file + `os.replace`) — applicable to any export/cache write ✅
- LRU cache invalidation on write ✅

**Required adaptation**:
- The JSON file sync itself is removed (Mapping Registry is source of truth)
- But the atomic write pattern should be reused for export operations

---

### 2.12 Keyword Learning Service

**File**: [keyword_learning.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/services/keyword_learning.py)

**What's reusable**:
- Auto-learning pattern (persist high-confidence classifications) ✅
- Upsert semantics (don't downgrade existing good entries) ✅

**Required adaptation**:
- Write to Mapping Registry instead of MetricKeyword table
- Include `relation_type=exactMatch` and `origin=auto-learned` on created rows

---

### 2.13 Seed Data

**File**: [seed_taxonomy_standards.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/scripts/seed_taxonomy_standards.py)

**What's reusable**:
- 15 `UNIFIED_KEYS` — well-curated CIM metric definitions ✅
- 20 `ALIAS_SEEDS` — high-quality raw→unified pairs ✅
- Seeding pattern (idempotent, auto-creates taxonomy + definitions) ✅

**Required adaptation**:
- Migrate to unified registry seed script
- Add quantity_kind and canonical_unit for each metric
- Migrate aliases to Mapping Registry format

---

### 2.14 MappingDecision Dataclass

**File**: [decision.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/ingestion/decision.py)

**What's reusable**:
- Frozen dataclass with unified_key, confidence, rationale, unit, tags ✅

**Required adaptation**:
- Add `relation_type` field

---

### 2.15 External JSON Exporter

**File**: [external_json.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/exporters/external_json.py)

**What's reusable**:
- `build_metadata()` function — site_id construction, ISO timestamp handling ✅
- `write_external_metrics_json()` — structured JSON export ✅
- Output format (`{metadata, metrics}`) ✅

**Required adaptation**:
- Source metadata from Asset Registry instead of inline parameters
- Add Standards Registry annotations to export
- Support additional export formats (RDF, CSV)

---

## 3. Reusable Seed Data Summary

| Source | Entries | Target Registry | Migration |
|--------|---------|----------------|-----------|
| `alias_classifier.ALIASES` | ~80 aliases | Mapping Registry | Convert to mapping rows with relation_type |
| `semantic_classifier.STANDARDS_MAP` | 10 rules | Mapping Registry | Convert to mapping rows linking source → CIM → standard |
| `seed_taxonomy_standards.UNIFIED_KEYS` | 15 keys | Metric Registry | Add label, description, quantity_kind, canonical_unit |
| `seed_taxonomy_standards.ALIAS_SEEDS` | 20 pairs | Mapping Registry | Convert to mapping rows |
| `standards_registry.SEED_STANDARDS` | 12 standards | Standards Registry | Extend with additional fields |
| `namespace_generator.CATEGORY_ALIASES` | 5 alias groups | Mapping Registry | Convert to mapping rows with relation_type=closeMatch |
| `namespace_generator.SUBCATEGORY_ALIASES` | 8 alias groups | Mapping Registry | Convert to mapping rows with relation_type=closeMatch |
| `ensemble_classifier._rule_guess` | ~20 rules | Rule Registry or Classification config | Keep as classification config |
| `ensemble_classifier._embed_guess` | 10 candidates | Mapping Registry or Classification config | Keep as classification config |

**Total reusable seed data**: ~180 entries that can be migrated into the target registries.

---

## 4. Reusable Architectural Patterns

| Pattern | Where Used | Reuse In Target |
|---------|-----------|----------------|
| **Cascading classifier** | `ensemble_classifier.py` | Classification Service — same pattern, registry-first |
| **Idempotent upsert** | `insert_mapped_metric.py`, `ensure_gd_namespace()` | All registry services |
| **Auto-learning** | `keyword_learning.py` | Mapping Registry auto-population |
| **Atomic file write** | `mapping_sync.py` | Export service |
| **Pydantic-settings config** | `config.py` | Unchanged |
| **Context-manager sessions** | `with SessionLocal() as s:` | All registry services (standardize this pattern) |
| **Lazy initialization** | `influx_service._ensure_client()` | Any heavy resource (model loading, DB connections) |
| **LRU cache + invalidation** | `namespace_mapper._load_mapping` | Registry query caching |
| **Rule-based standards inference** | `standards_registry._guess_standard_codes()` | Standards linkage service |
| **Confidence-scored linking** | `MetricStandardMap.confidence` | Mapping Registry confidence scores |

---

## 5. Reuse Summary

| Category | Count | % of Total |
|----------|-------|------------|
| Fully reusable (no changes) | 7 components | 13% |
| Reusable with minor adaptation | 15 components | 27% |
| Reusable seed data | ~180 entries | — |
| Reusable patterns | 10 patterns | — |
| **Total reusable** | **22 components + 180 data entries + 10 patterns** | **~40% of codebase** |
