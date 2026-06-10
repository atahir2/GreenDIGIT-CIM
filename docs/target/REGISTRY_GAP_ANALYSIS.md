# Registry Gap Analysis

> **Generated**: 2026-06-10 · **Scope**: Detailed gap analysis per target registry

---

## 1. Gap Overview Dashboard

| # | Registry | Tables Exist | Services Exist | Seed Data | Validation | API | Tests | Overall |
|---|----------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 1 | Metric Registry | 🟡 Partial | 🟡 Partial | 🟡 Partial | ❌ | ❌ | ❌ | 🟡 40% |
| 2 | Unit Registry | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | 🔴 0% |
| 3 | Source Registry | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | 🔴 5% |
| 4 | Asset Registry | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | 🔴 5% |
| 5 | Standards Registry | ✅ Good | ✅ Good | ✅ 12 seeded | ❌ | ❌ | ❌ | 🟢 65% |
| 6 | Mapping Registry | 🟡 Fragmented | 🟡 Fragmented | 🟡 ~80 aliases | ❌ | ❌ | ❌ | 🟡 30% |
| 7 | Lifecycle Registry | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | 🔴 0% |
| 8 | Rule Registry | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | 🔴 0% |
| 9 | Evidence Registry | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | 🔴 0% |
| 10 | Provenance Registry | 🟡 Model only | ❌ | ❌ | ❌ | ❌ | ❌ | 🔴 5% |
| 11 | Extension Registry | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | 🔴 0% |

---

## 2. Detailed Gap Analysis per Registry

### 2.1 Metric Registry — 🟡 40% Coverage

#### What Exists

| Component | Status | Notes |
|-----------|--------|-------|
| `metric_definitions` table | ✅ | Has unified_key (unique), tags, sources, created_at |
| `categories` table | ✅ | Has name (unique), description, standard_id FK |
| `subcategories` table | ✅ | Has name, category_id FK, description |
| `insert_mapped_metric()` service | ✅ | Upserts MetricDefinition, merges sources/tags |
| `ensure_gd_namespace()` | ✅ | Auto-creates taxonomy rows |
| `to_gd()` normalization | ✅ | Ensures `gd.*` prefix |
| Seed data | 🟡 | 15 unified keys in `seed_taxonomy_standards.py` |

#### What's Missing

| Gap | Priority | Effort |
|-----|----------|--------|
| `label` field (human-readable name) | High | Low |
| `description` field on metric_definitions | High | Low |
| `domain` field (energy, performance, etc.) | Medium | Low |
| `quantity_kind` FK to Unit Registry | High | Medium |
| `canonical_unit` FK to Unit Registry | High | Medium |
| `metric_type` enum (observed/calculated/derived/aggregated/reported) | High | Low |
| `status` enum (draft/active/deprecated/retired) | Medium | Low |
| `version` field | Low | Low |
| `updated_at` timestamp | Low | Low |
| Metric Registry CRUD API | High | Medium |
| Metric Registry validation service | Medium | Medium |
| Metric Registry tests | High | Medium |

---

### 2.2 Unit Registry — 🔴 0% Coverage

#### What Exists

| Component | Status | Notes |
|-----------|--------|-------|
| `unit_normalizer.py` regex extraction | 🟡 | Extracts %, MB, GB, W from raw values — no validation or conversion |
| `unit` nullable field on `metric_samples` | 🟡 | Stores unit strings but doesn't validate |

#### What's Missing

| Gap | Priority | Effort |
|-----|----------|--------|
| `units` table (symbol, name, quantity_kind, conversion_factor/offset) | High | Medium |
| `quantity_kinds` table (Energy, Power, Temperature, DataSize, etc.) | High | Low |
| QUDT alignment (URI mapping) | Medium | Medium |
| Unit conversion service | High | Medium |
| Unit validation service (reject invalid unit for quantity kind) | High | Medium |
| Power vs. Energy distinction enforcement | High | Low |
| Seed data: common units (kWh, W, °C, GB, Mbps, etc.) | High | Low |
| Unit Registry CRUD API | Medium | Medium |
| Unit Registry tests | High | Medium |

---

### 2.3 Source Registry — 🔴 5% Coverage

#### What Exists

| Component | Status | Notes |
|-----------|--------|-------|
| `datacenters` table | 🟡 | Has name, location, provider — but models sites, not source systems |
| `file_upload_logs` table | 🟡 | Tracks uploads but not source capabilities |
| `aws.py`, `gcp.py` stubs | 🟡 | Represent source concept but are hardcoded stubs |
| `ingest_any.py` format detection | 🟡 | Detects JSON/YAML/XML/CSV/TXT — represents format awareness |

#### What's Missing

| Gap | Priority | Effort |
|-----|----------|--------|
| `sources` table (name, type, protocol, format, capabilities, auth, status) | High | Medium |
| Source type enum (file, api, prometheus, opentelemetry, scaphandre, manual) | High | Low |
| Source capability metadata (what metrics a source can provide) | Medium | Medium |
| Source connector framework (pluggable adapters) | Medium | High |
| Prometheus scrape endpoint support | Medium | High |
| OpenTelemetry OTLP receiver | Medium | High |
| Scaphandre connector | Medium | Medium |
| Source Registry CRUD API | Medium | Medium |
| Source Registry tests | High | Medium |

---

### 2.4 Asset Registry — 🔴 5% Coverage

#### What Exists

| Component | Status | Notes |
|-----------|--------|-------|
| `datacenters` table | 🟡 | Top-level asset only. No hierarchy |
| `ri_id`, `node_id`, `vm_id`, `host` on `metric_samples` | 🟡 | Asset metadata stored per-sample, not normalized |
| `site_id` construction | 🟡 | Composite key in metadata extraction |

#### What's Missing

| Gap | Priority | Effort |
|-----|----------|--------|
| `assets` table (name, type, parent_id, location, provider, specs, lifecycle_stage, status) | High | Medium |
| Asset type hierarchy (datacenter → cluster → rack → node → cpu/gpu/vm/container) | High | Medium |
| Research objects (workflow, dataset, experiment) | Medium | Medium |
| Asset-metric linkage (which asset produces which metrics) | High | Low |
| Asset lifecycle stage FK | Medium | Low |
| Asset specifications JSONB (CPU model, TDP, memory, etc.) | Medium | Low |
| Asset Registry CRUD API | Medium | Medium |
| Asset hierarchy navigation API | Medium | Medium |
| Migration: extract ri_id/node_id/vm_id/host from samples → assets | High | Medium |
| Asset Registry tests | High | Medium |

---

### 2.5 Standards Registry — 🟢 65% Coverage

#### What Exists

| Component | Status | Notes |
|-----------|--------|-------|
| `standards` table | ✅ | Has code, name, url, description |
| `metric_standard_map` table | ✅ | Links metrics to standards with confidence + rationale |
| `ensure_seed_standards()` | ✅ | Seeds 12 standards |
| `attach_standard()` | ✅ | Rule-based standards linkage |
| `_guess_standard_codes()` | ✅ | Inference rules |

#### What's Missing

| Gap | Priority | Effort |
|-----|----------|--------|
| Missing standards: SAREF, SOSA/SSN, QUDT, schema.org, PROV-O, DCAT, RO-Crate, OTel conventions, EN 50600, OCP, ISO 14040/14044, ISO 14001 | High | Low |
| `vocabulary_type` field (standard, ontology, vocabulary, convention) | Medium | Low |
| `namespace_prefix` + `namespace_uri` fields | High | Low |
| `version` field | Low | Low |
| `domain` field | Low | Low |
| `status` field (active/superseded/draft) | Low | Low |
| Standards Registry CRUD API | Medium | Medium |
| Standards Registry tests | High | Medium |

---

### 2.6 Mapping Registry — 🟡 30% Coverage

#### What Exists

| Component | Status | Notes |
|-----------|--------|-------|
| `metric_source_map` table | 🟡 | Per-DC raw→unified mapping with timestamps |
| `metric_keywords` table | 🟡 | Learned raw→taxonomy cache |
| `metric_mappings` table | 🟡 | Model exists but **never populated** |
| `mapping_proposals` table | 🟡 | Model exists but **never populated** |
| `mapping_events` table | 🟡 | Model exists but **never populated** |
| `metric_mapping.json` (2 files) | 🟡 | File-based mapping cache |
| `mapping_sync.py` | ✅ | Atomic JSON file sync |
| `register_mapping()` | 🟡 | Writes to metric_source_map + JSON but not metric_mappings |
| `resolve_unified_key()` | 🟡 | Reads from metric_mappings (which is empty) |
| ~80 aliases in `alias_classifier.py` | ✅ | Hardcoded but valuable seed data |
| 10 entries in `semantic_classifier.py` | ✅ | Hardcoded but valuable seed data |
| ~20 alias pairs in `seed_taxonomy_standards.py` | ✅ | Seeded keyword mappings |

#### What's Missing

| Gap | Priority | Effort |
|-----|----------|--------|
| **Relation type** enum (exactMatch, closeMatch, broadMatch, narrowMatch, inputToKPI, derivedFrom, contextualMatch, extensionMetric, noMatch, underReview) | **Critical** | Low |
| Unified mapping table (merge metric_source_map + metric_keywords + metric_mappings) | High | Medium |
| `source_id` FK to Source Registry | High | Low |
| `cim_metric_id` FK to Metric Registry | High | Low |
| `standard_id` FK to Standards Registry (for standard↔CIM mappings) | High | Low |
| `approved_by` field | Medium | Low |
| `status` field (proposed/approved/rejected/deprecated) | High | Low |
| **Activate** the existing proposal/approval workflow | High | Medium |
| Migrate hardcoded aliases into Mapping Registry rows | High | Medium |
| Migrate semantic_classifier entries into Mapping Registry | High | Low |
| Remove dual JSON file approach (single DB source of truth) | Medium | Medium |
| Mapping Registry CRUD API | High | Medium |
| Mapping Registry search (by source, by CIM metric, by standard) | High | Medium |
| Mapping Registry tests | High | Medium |

---

### 2.7 Lifecycle Registry — 🔴 0% Coverage

#### What Exists

Nothing.

#### What's Missing

| Gap | Priority | Effort |
|-----|----------|--------|
| `lifecycle_stages` table (10 stages: planning through decommissioning) | Medium | Low |
| `metric_lifecycle_map` M2M table | Medium | Low |
| `asset_lifecycle_map` M2M table | Medium | Low |
| Seed data (10 stages with descriptions) | Medium | Low |
| Lifecycle Registry CRUD API | Low | Medium |
| Lifecycle Registry tests | Medium | Low |

---

### 2.8 Rule Registry — 🔴 0% Coverage

#### What Exists

Implicit rules scattered in code:
- `to_gd()` enforces namespace format
- `captured_at` is NOT NULL in MetricSample
- `unified_key` is UNIQUE in MetricDefinition

#### What's Missing

| Gap | Priority | Effort |
|-----|----------|--------|
| `validation_rules` table (name, description, rule_type, target, condition, severity, status) | High | Medium |
| Rule engine (JSONLogic, JSONSchema, or custom evaluator) | High | High |
| Seed rules: namespace requirement, unit requirement, timestamp+source, power vs energy, formula for calculated, boundary+period for KPIs | High | Medium |
| Rule execution service (validate metric sample against rules) | High | High |
| Rule violation logging | Medium | Medium |
| Rule Registry CRUD API | Medium | Medium |
| Rule Registry tests | High | Medium |

---

### 2.9 Evidence Registry — 🔴 0% Coverage

#### What Exists

Nothing directly. `metric_standard_map.confidence` and `rationale` hint at evidence but are not structured.

#### What's Missing

| Gap | Priority | Effort |
|-----|----------|--------|
| `evidence_requirements` table | Medium | Medium |
| Evidence type enum (measurement, calculation, document, audit) | Medium | Low |
| Reporting period specification | Medium | Low |
| Aggregation method specification | Medium | Low |
| Boundary specification (site/facility/IT/total) | Medium | Low |
| Certification readiness assessment service | Low | High |
| Evidence Registry CRUD API | Low | Medium |
| Evidence Registry tests | Medium | Medium |

---

### 2.10 Provenance Registry — 🔴 5% Coverage

#### What Exists

| Component | Status | Notes |
|-----------|--------|-------|
| `mapping_events` table | 🟡 | Model exists but **never written to** |
| `file_upload_logs` table | 🟡 | Tracks file uploads (ingestion provenance) |
| `clf_confidence` / `clf_rationale` on `metric_samples` | 🟡 | Per-sample classification provenance |
| `first_seen` / `last_seen` on `metric_source_map` | 🟡 | Temporal tracking |

#### What's Missing

| Gap | Priority | Effort |
|-----|----------|--------|
| Unified `provenance_records` table | High | Medium |
| Activity types: ingestion, classification, mapping, unit_conversion, aggregation, export, approval | High | Low |
| PROV-O alignment (Entity, Activity, Agent) | Medium | Medium |
| Agent tracking (system, user, API key) | Medium | Low |
| Input/output JSONB fields | Medium | Low |
| Duration tracking (started_at, ended_at) | Low | Low |
| Activate `mapping_events` writes | High | Low |
| Migrate `file_upload_logs` to provenance | Medium | Low |
| Provenance Registry query API | Medium | Medium |
| Provenance Registry tests | High | Medium |

---

### 2.11 Extension Registry — 🔴 0% Coverage

#### What Exists

Implicit — any metric classified as `gd.uncategorized.*` or `gd.custom.*` is effectively an unstandardized extension.

#### What's Missing

| Gap | Priority | Effort |
|-----|----------|--------|
| `extensions` table | Low | Low |
| Extension proposal workflow | Low | Medium |
| Link to candidate standard | Low | Low |
| Extension status tracking | Low | Low |
| Extension Registry CRUD API | Low | Medium |
| Extension Registry tests | Low | Low |

---

## 3. Cross-Cutting Gaps

### 3.1 Schema Management

| Gap | Priority | Current State |
|-----|----------|---------------|
| Alembic migrations | **Critical** | No migrations. `create_schema.py` does create_all() |
| Migration for registry expansion | **Critical** | Cannot add columns without migrations |
| Rollback capability | High | None |

### 3.2 API Layer

| Gap | Priority | Current State |
|-----|----------|---------------|
| Registry CRUD endpoints (all 11) | High | Only `/metrics/aws|gcp` and `/query` exist |
| OpenAPI documentation | Medium | FastAPI auto-generates but needs schema enrichment |
| Authentication/Authorization | Medium | No auth on any endpoint |
| Pagination | Low | No pagination on queries |

### 3.3 Test Coverage

| Gap | Priority | Current State |
|-----|----------|---------------|
| Registry service unit tests | **Critical** | 0 tests for any registry |
| Classifier tests | High | 0 tests |
| Parser tests | High | 0 tests |
| Integration tests | Medium | 0 tests |
| Mapping Registry tests | High | 0 tests (existing test broken) |
| End-to-end ingestion test | Medium | 0 tests |

---

## 4. Effort Estimation Summary

| Category | Items | Estimated Effort |
|----------|-------|-----------------|
| New database models (6 registries) | Unit, Source, Asset, Lifecycle, Rule, Evidence, Extension, Provenance | ~3–4 days |
| Schema extensions (existing models) | Metric, Standard, Mapping consolidation | ~2 days |
| Alembic setup + migrations | Initial setup + registry migrations | ~1 day |
| Registry services (11 registries) | CRUD + validation + seed | ~5–7 days |
| Classification pipeline refactor | Single pipeline, Mapping Registry integration | ~2–3 days |
| Ingestion pipeline refactor | Source/Asset resolution, Unit conversion, Rule validation, Provenance | ~3–4 days |
| API endpoints | 11 registry CRUD endpoints + search | ~3–4 days |
| Seed data | Standards, units, lifecycle stages, rules, aliases→mappings | ~2 days |
| Test suite | Registry tests, classifier tests, parser tests, integration | ~4–5 days |
| Dead code removal + cleanup | Remove duplicates, commented code, unused modules | ~1 day |
| **Total** | | **~26–35 days** |
