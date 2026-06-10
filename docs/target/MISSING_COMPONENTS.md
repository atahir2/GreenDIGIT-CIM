# Missing Components

> **Generated**: 2026-06-10 · **Scope**: Complete inventory of components that must be created for the target architecture

---

## 1. Missing Database Models

### 1.1 Unit Registry Models

| Model | Table | Key Fields | Priority |
|-------|-------|------------|----------|
| `QuantityKind` | `quantity_kinds` | id, name (Energy, Power, Temperature, DataSize, DataRate, Percentage, Time, Count), description, qudt_uri | High |
| `Unit` | `units` | id, symbol (kWh, W, °C, GB, Mbps), name, quantity_kind_id FK, si_base, canonical_unit_id FK→self, conversion_factor, conversion_offset, qudt_uri, saref_uri | High |

**Seed data required**: ~30 units across 8 quantity kinds

```
Energy: Wh, kWh, MWh, J, kJ, MJ
Power: W, kW, MW, VA, kVA
Temperature: °C, °F, K
DataSize: B, KB, MB, GB, TB, PB
DataRate: bps, Kbps, Mbps, Gbps
Percentage: %
Time: s, ms, min, h, d
Count: count, cores
```

---

### 1.2 Source Registry Models

| Model | Table | Key Fields | Priority |
|-------|-------|------------|----------|
| `Source` | `sources` | id, name, type (file/api/prometheus/opentelemetry/scaphandre/manual), protocol, format, schema_version, capabilities (JSONB), auth_method, status, metadata (JSONB), created_at, updated_at | High |

**Seed data required**: Initial source types for partner file uploads, AWS CloudWatch, GCP Monitoring

---

### 1.3 Asset Registry Models

| Model | Table | Key Fields | Priority |
|-------|-------|------------|----------|
| `Asset` | `assets` | id, name, type (datacenter/cluster/rack/node/server/cpu/gpu/storage_system/network_device/vm/container/service/workflow/dataset/experiment), parent_id FK→self, location, provider, specifications (JSONB), lifecycle_stage FK, status, created_at, updated_at | High |

**Migration required**: Existing `datacenters` table data → `assets` with `type='datacenter'`

---

### 1.4 Unified Mapping Registry Models

| Model | Table | Key Fields | Priority |
|-------|-------|------------|----------|
| `CimMapping` | `cim_mappings` | id, source_key, source_id FK→sources, cim_metric_id FK→metric_definitions, standard_id FK→standards (nullable), relation_type (exactMatch/closeMatch/broadMatch/narrowMatch/inputToKPI/derivedFrom/contextualMatch/extensionMetric/noMatch/underReview), confidence, rationale, approved_by, approved_at, status (proposed/approved/rejected/deprecated), version, origin (manual/auto-learned/seeded/imported), created_at, updated_at | **Critical** |

**Migration required**: Merge data from `metric_source_map`, `metric_keywords`, and hardcoded aliases into this table

---

### 1.5 Lifecycle Registry Models

| Model | Table | Key Fields | Priority |
|-------|-------|------------|----------|
| `LifecycleStage` | `lifecycle_stages` | id, stage (planning/design/procurement/deployment/operation/optimisation/reproducibility/reporting/continuous_improvement/decommissioning), label, description, sequence | Medium |
| `MetricLifecycleMap` | `metric_lifecycle_map` | id, metric_id FK, lifecycle_stage_id FK, relevance (primary/secondary/optional) | Medium |
| `AssetLifecycleMap` | `asset_lifecycle_map` | id, asset_id FK, lifecycle_stage_id FK, entered_at, exited_at | Medium |

**Seed data required**: 10 lifecycle stages with descriptions

---

### 1.6 Rule Registry Models

| Model | Table | Key Fields | Priority |
|-------|-------|------------|----------|
| `ValidationRule` | `validation_rules` | id, name, description, rule_type (required_field/type_check/range_check/cross_field/formula/constraint), target_registry, condition (JSONB), severity (error/warning/info), status (active/disabled), created_at | High |
| `RuleViolation` | `rule_violations` | id, rule_id FK, entity_type, entity_id, violation_detail (JSONB), resolved, created_at | Medium |

**Seed rules required**:

| Rule | Type | Severity |
|------|------|----------|
| Every metric must have a namespace (gd.*) | required_field | error |
| Every numeric metric must have a unit | required_field | error |
| Every observed metric must have timestamp and source | required_field | error |
| Every energy metric must distinguish power (W) from energy (kWh) | cross_field | error |
| Every calculated metric must have a formula reference | required_field | warning |
| Every reportable KPI must have boundary and aggregation period | required_field | warning |
| PUE must be ≥ 1.0 | range_check | error |
| Temperature must be -50°C to 150°C | range_check | warning |
| Percentage must be 0–100 | range_check | warning |

---

### 1.7 Evidence Registry Models

| Model | Table | Key Fields | Priority |
|-------|-------|------------|----------|
| `EvidenceRequirement` | `evidence_requirements` | id, standard_id FK, metric_id FK, evidence_type (measurement/calculation/document/audit), requirement_level (mandatory/recommended/optional), reporting_period, aggregation_method, boundary, description, created_at | Medium |
| `EvidenceRecord` | `evidence_records` | id, requirement_id FK, asset_id FK, period_start, period_end, evidence_data (JSONB), status (pending/submitted/accepted/rejected), submitted_by, submitted_at | Low |

---

### 1.8 Provenance Registry Models

| Model | Table | Key Fields | Priority |
|-------|-------|------------|----------|
| `ProvenanceRecord` | `provenance_records` | id, entity_type (metric_sample/cim_mapping/metric_definition), entity_id, activity (ingestion/classification/mapping/unit_conversion/aggregation/export/approval), agent (system_component/user_id), started_at, ended_at, inputs (JSONB), outputs (JSONB), method, confidence, prov_uri, created_at | High |

---

### 1.9 Extension Registry Models

| Model | Table | Key Fields | Priority |
|-------|-------|------------|----------|
| `Extension` | `extensions` | id, metric_id FK, proposed_standard, justification, status (proposed/accepted/submitted_to_standard/adopted), proposed_by, proposed_at, reviewed_at | Low |

---

## 2. Missing Services

### 2.1 Registry Services (CRUD + Business Logic)

| Service | Module | Key Functions | Priority |
|---------|--------|---------------|----------|
| `unit_registry_service.py` | `cloud_metrics/services/` | `create_unit()`, `get_unit()`, `convert_value()`, `validate_unit_for_quantity()`, `get_canonical_unit()` | High |
| `source_registry_service.py` | `cloud_metrics/services/` | `create_source()`, `get_source()`, `resolve_source()`, `list_sources()` | High |
| `asset_registry_service.py` | `cloud_metrics/services/` | `create_asset()`, `get_asset()`, `get_hierarchy()`, `resolve_asset_from_metadata()` | High |
| `mapping_registry_service.py` | `cloud_metrics/services/` | `create_mapping()`, `resolve_mapping()`, `approve_mapping()`, `reject_mapping()`, `auto_learn_mapping()`, `search_mappings()` | **Critical** |
| `lifecycle_registry_service.py` | `cloud_metrics/services/` | `create_stage()`, `link_metric_to_stage()`, `link_asset_to_stage()`, `get_metrics_for_stage()` | Medium |
| `rule_registry_service.py` | `cloud_metrics/services/` | `create_rule()`, `validate_metric_sample()`, `validate_metric_definition()`, `log_violation()` | High |
| `evidence_registry_service.py` | `cloud_metrics/services/` | `create_requirement()`, `check_readiness()`, `submit_evidence()` | Medium |
| `provenance_registry_service.py` | `cloud_metrics/services/` | `record_activity()`, `get_provenance_chain()`, `query_provenance()` | High |
| `extension_registry_service.py` | `cloud_metrics/services/` | `propose_extension()`, `review_extension()` | Low |
| `metric_registry_service.py` | `cloud_metrics/services/` | Unified CRUD wrapping existing `insert_mapped_metric()` + new fields | High |

---

### 2.2 Unit Conversion Service

**Does not exist at all.** Currently, units are extracted via regex but never validated or converted.

```python
# Required functionality:
def convert_value(value: float, from_unit: str, to_unit: str) -> float:
    """Convert between units of the same quantity kind."""
    
def get_canonical_unit(quantity_kind: str) -> Unit:
    """Return the canonical unit for a quantity kind (e.g., Energy → kWh)."""
    
def validate_unit(unit: str, quantity_kind: str) -> bool:
    """Check if a unit is valid for a given quantity kind."""
```

---

### 2.3 Rule Validation Service

**Does not exist.** Validation is currently scattered as implicit checks in code.

```python
# Required functionality:
def validate_metric_sample(sample: MetricSample) -> list[RuleViolation]:
    """Run all active rules against a metric sample."""
    
def validate_metric_definition(definition: MetricDefinition) -> list[RuleViolation]:
    """Run all active rules against a metric definition."""
```

---

### 2.4 Provenance Service

**Does not exist.** `mapping_events` model exists but is never written to.

```python
# Required functionality:
def record_activity(
    entity_type: str, entity_id: int,
    activity: str, agent: str,
    inputs: dict, outputs: dict,
    method: str, confidence: float
) -> ProvenanceRecord:
    """Record a provenance entry for any system activity."""
```

---

## 3. Missing API Endpoints

### 3.1 Registry CRUD Endpoints

Each registry needs at minimum:

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `POST` | `/api/v1/{registry}/` | Create entry |
| `GET` | `/api/v1/{registry}/` | List entries (with pagination + filters) |
| `GET` | `/api/v1/{registry}/{id}` | Get single entry |
| `PUT` | `/api/v1/{registry}/{id}` | Update entry |
| `DELETE` | `/api/v1/{registry}/{id}` | Delete/deprecate entry |

**Registries needing endpoints**: metrics, units, sources, assets, standards, mappings, lifecycle, rules, evidence, provenance, extensions

**Total new endpoints**: ~55 (5 per registry × 11 registries)

### 3.2 Specialized Endpoints

| Endpoint | Purpose | Priority |
|----------|---------|----------|
| `POST /api/v1/ingest/` | Unified ingestion endpoint (replaces `/metrics/aws`, `/metrics/gcp`) | High |
| `POST /api/v1/ingest/file` | File-based ingestion | High |
| `GET /api/v1/mappings/resolve/{raw_key}` | Resolve a raw key to CIM mapping | High |
| `POST /api/v1/mappings/approve/{id}` | Approve a proposed mapping | High |
| `POST /api/v1/mappings/bulk-import` | Bulk import mappings | Medium |
| `GET /api/v1/assets/{id}/hierarchy` | Get asset hierarchy tree | Medium |
| `GET /api/v1/assets/{id}/metrics` | Get metrics for an asset | Medium |
| `POST /api/v1/rules/validate` | Validate a metric sample against rules | High |
| `GET /api/v1/evidence/readiness/{standard_id}` | Check certification readiness | Low |
| `GET /api/v1/provenance/{entity_type}/{entity_id}` | Get provenance chain | Medium |
| `GET /api/v1/export/json` | Export metrics with standards annotations | Medium |
| `GET /api/v1/export/rdf` | Export as linked data | Low |

---

## 4. Missing Validation Rules

| Rule | Target Registry | Currently Enforced? | Priority |
|------|----------------|--------------------|----|
| Every metric_definition must have a non-empty namespace | Metric | ✅ `to_gd()` ensures prefix | — |
| Every metric_definition must have quantity_kind | Metric | ❌ Field doesn't exist | High |
| Every metric_definition must have canonical_unit | Metric | ❌ Field doesn't exist | High |
| Every metric_definition must have metric_type | Metric | ❌ Field doesn't exist | High |
| Every metric_sample must have a unit | Rule | ❌ `unit` is nullable | High |
| Every metric_sample must have captured_at + source | Rule | 🟡 `captured_at` NOT NULL, `source_file` nullable | Medium |
| Energy metric unit must be in Energy quantity kind | Rule | ❌ No unit validation | High |
| Power metric unit must be in Power quantity kind | Rule | ❌ No unit validation | High |
| Calculated metrics must reference a formula | Rule | ❌ No formula storage | Medium |
| KPIs must have boundary + aggregation period | Rule | ❌ No KPI metadata | Medium |
| PUE must be ≥ 1.0 | Rule | ❌ No range check | Medium |
| Temperature must be reasonable (-50 to 150°C) | Rule | ❌ No range check | Low |
| Every mapping must have a relation_type | Mapping | ❌ No relation types | High |
| Every mapping must have a source_id | Mapping | ❌ No source tracking | High |
| Every approved mapping must have approved_by | Mapping | ❌ No approval tracking | Medium |

---

## 5. Missing Tests

### 5.1 Registry Service Tests

| Test File | Tests Needed | Priority |
|-----------|-------------|----------|
| `test_metric_registry.py` | CRUD, validation, namespace format, quantity_kind linkage | High |
| `test_unit_registry.py` | CRUD, conversion accuracy, quantity_kind validation, edge cases | High |
| `test_source_registry.py` | CRUD, type validation, capability metadata | High |
| `test_asset_registry.py` | CRUD, hierarchy navigation, type validation, migration from datacenters | High |
| `test_mapping_registry.py` | CRUD, relation types, resolve, approve/reject, auto-learn, bulk import | **Critical** |
| `test_lifecycle_registry.py` | CRUD, metric/asset linking, stage sequencing | Medium |
| `test_rule_registry.py` | CRUD, validation execution, violation logging | High |
| `test_evidence_registry.py` | CRUD, readiness check, period handling | Medium |
| `test_provenance_registry.py` | CRUD, activity recording, chain traversal | High |
| `test_extension_registry.py` | CRUD, status transitions | Low |
| `test_standards_registry.py` | Extended seed validation, vocabulary type handling | Medium |

### 5.2 Classification & Mapping Tests

| Test File | Tests Needed | Priority |
|-----------|-------------|----------|
| `test_ensemble_classifier.py` | Each layer independently, cascade behavior, unknown handling, confidence thresholds | High |
| `test_alias_classifier.py` | Fuzzy matching accuracy, cutoff behavior, edge cases | High |
| `test_semantic_classifier.py` | Exact match coverage, normalization edge cases | Medium |
| `test_fallback_classifier.py` | Proper output format, relation_type=noMatch | Medium |
| `test_classification_pipeline.py` | End-to-end: raw_key → Mapping Registry query → classifier → registration | High |

### 5.3 Parser Tests

| Test File | Tests Needed | Priority |
|-----------|-------------|----------|
| `test_structured_parser.py` | JSON, YAML, CSV, XML, NDJSON, edge cases (BOM, empty, malformed) | High |
| `test_unstructured_parser.py` | All 6 patterns, edge cases, multiple matches, no matches | Medium |
| `test_ingest_any.py` | All 3 strategies, all formats, metadata extraction, domain detection | High |
| `test_partner_payload.py` | Cloud/grid/network payloads, missing fields, extra fields | High |

### 5.4 Service Tests

| Test File | Tests Needed | Priority |
|-----------|-------------|----------|
| `test_unit_conversion.py` | All quantity kinds, edge cases (0, negative, very large), °F→°C offset | High |
| `test_rule_validation.py` | Each seed rule, violation logging, severity levels | High |
| `test_provenance_service.py` | Activity recording, chain building, query filtering | Medium |
| `test_ingestion_pipeline.py` | Full pipeline: parse → classify → map → validate → persist → provenance | High |

### 5.5 API Tests

| Test File | Tests Needed | Priority |
|-----------|-------------|----------|
| `test_registry_api.py` | CRUD for all registries, validation errors, pagination | High |
| `test_ingest_api.py` | File upload, JSON payload, error handling | High |
| `test_export_api.py` | JSON export, RDF export, filters | Medium |

### 5.6 Integration Tests

| Test File | Tests Needed | Priority |
|-----------|-------------|----------|
| `test_integration_ingestion.py` | End-to-end file ingestion with all registries | Medium |
| `test_integration_mapping_lifecycle.py` | Propose → approve → apply mapping with provenance | Medium |

---

## 6. Missing Infrastructure

| Component | Current State | Required | Priority |
|-----------|--------------|----------|----------|
| Alembic migrations | Not configured | Essential for schema evolution | **Critical** |
| `alembic.ini` + `migrations/` directory | Missing | Setup + initial migration | **Critical** |
| API authentication | None | API key or OAuth2 | Medium |
| API rate limiting | None | Rate limiter middleware | Low |
| Structured logging | `print()` statements | Python `logging` + JSON formatter | Medium |
| Health checks | `/health` exists | Add DB + InfluxDB connectivity checks | Low |
| Docker Compose fixes | Port mismatches, no volumes | Fix ports, add volumes, secrets management | Medium |
| CI pipeline expansion | Basic pytest | Add linting, type checking, coverage reporting | Medium |

---

## 7. Missing Seed Data

| Registry | Entries Needed | Source |
|----------|---------------|--------|
| **Units** | ~30 units, ~8 quantity kinds | QUDT vocabulary |
| **Sources** | ~5 initial sources (file_upload, aws_cloudwatch, gcp_monitoring, prometheus, manual) | Manual definition |
| **Lifecycle** | 10 stages with descriptions | Target spec |
| **Rules** | ~15 validation rules | Target spec |
| **Standards** (extension) | ~12 additional (SAREF, QUDT, PROV-O, DCAT, RO-Crate, OTel, EN 50600, OCP, ISO 14040, ISO 14044, ISO 14001, schema.org) | Manual definition |
| **Mappings** (migration) | ~180 entries from hardcoded aliases + semantic map + keyword seeds | Migrate from code |
| **Evidence** | Requirements per standard (PUE measurement for TGG, emissions for GHG, etc.) | Manual definition |
