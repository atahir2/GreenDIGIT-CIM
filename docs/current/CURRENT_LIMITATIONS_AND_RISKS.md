# Current Limitations & Risks — GreenDIGIT CIM

> **Generated**: 2026-06-10 · **Scope**: Full technical debt and risk audit (read-only)

---

## 1. Critical Issues

### 1.1 Duplicated Classification Logic

| Location | What it does |
|----------|-------------|
| [ensemble_classifier.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/classifiers/ensemble_classifier.py) `classify_metric()` | 5-layer cascade: semantic → alias → rules → embeddings → fallback |
| [automated_mapper.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/ingestion/automated_mapper.py#L55-L130) `_classify_to_parts()` | Independent 4-layer cascade: semantic → DB keywords → alias → rules |

**Risk**: `_classify_to_parts()` is defined but **not called in the main flow** (L166 calls `classify_metric()` instead). However, it contains unique logic (DB keyword lookup) that the ensemble classifier lacks. If someone calls `_classify_to_parts()` expecting it to be the canonical path, results will differ. The two functions also use **different fuzzy cutoffs** (90 vs 88).

**Impact**: High — divergent classification results if the wrong function is called.

---

### 1.2 Dead Code in Fallbacks

**File**: [fallbacks.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/classifiers/fallbacks.py#L18-L19)

```python
def fallback_namespace_from_raw(raw_key: str, unit_hint: str | None = None):
    short = "".join(_tokens(raw_key)) or "unknown"
    return "custom", "unknown", short       # ← LINE 19: unconditional return

    t = _tokens(raw_key)                    # ← LINE 21: UNREACHABLE
    slug = lambda s: "".join(_tokens(s)) or "unknown"
    if len(t) == 1:
        a = t[0]
        if a == "pue":
            return "energy","efficiency","pue"
        # ... 30+ lines of sophisticated fallback logic
```

**Impact**: Medium — PUE, CFP, unit-driven hints, and intelligent token slugging are all dead. Every unknown metric gets `("custom", "unknown", concatenated_tokens)`.

---

### 1.3 Datacenter Names Stored as Source Keys

**File**: [automated_mapper.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/ingestion/automated_mapper.py#L217)

```python
insert_mapped_metric(unified_key=unified_key, source_keys=[origin], tags=tags)
```

`origin` is the **datacenter name** (e.g., "datacenter_A"), not the raw metric key. This causes:
- `metric_definitions.sources` to contain datacenter names instead of raw keys
- `metric_mapping.json` to contain entries like `"gd.energy.consumption.total": ["datacenter_A", "30", "q"]`
- Reverse lookups (`map_raw_to_unified`) to **fail** because it searches for raw metric keys but finds datacenter names

**Impact**: High — the JSON mapping file is polluted and reverse lookups are unreliable.

---

### 1.4 Hardcoded datacenter_id = 1

**Files**:
- [unified_ingestion.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/ingestion/unified_ingestion.py#L74): `datacenter_id=1`
- [realtime_ingestor.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/ingestion/realtime_ingestor.py#L34): `datacenter_id=1`

```python
insert_file_upload_log(
    filename=...,
    datacenter_id=1,  # replace with actual lookup logic if needed
    ...
)
```

**Impact**: Medium — all upload logs link to datacenter ID 1 regardless of actual datacenter. This is especially problematic for multi-tenant deployments.

---

### 1.5 Unused ORM Tables

Three tables have complete SQLAlchemy models but **no code writes to them**:

| Table | Model | Status |
|-------|-------|--------|
| `metric_mappings` | `MetricMapping` | Read by `registry_service.py` but never populated |
| `mapping_proposals` | `MappingProposal` | Fully defined but completely unused |
| `mapping_events` | `MappingEvent` | Fully defined but completely unused |

**Impact**: Medium — the proposal/approval workflow and audit trail are architecturally designed but non-functional.

---

## 2. Architectural Issues

### 2.1 Two Incompatible Mapping JSON Formats

| File | Schema | Updated By |
|------|--------|-----------|
| `cloud_metrics/mapping/metric_mapping.json` | `{ unified: [source1, source2] }` | `mapping_sync.py` |
| `cloud_metrics/data/metric_mapping.json` | `{ raw_key: {unified_key, last_seen} }` | `rebuild_mapping_json.py` |

These represent the **same conceptual data** (raw↔unified mappings) but in different formats and are maintained independently. The runtime path uses the `mapping/` version; the export/data version is a separate snapshot.

---

### 2.2 Three Different PartnerMeta/IngestMeta Dataclasses

| Dataclass | File | Fields |
|-----------|------|--------|
| `PartnerMeta` | `utils/ingest_any.py` | domain, datacenter, site_id, captured_at, ri_id, node_id, vm_id, host, extra |
| `PartnerMeta` | `utils/partner_payload.py` | domain, datacenter, site_id, captured_at, ri_id, node_id, vm_id, host, extra |
| `IngestMeta` | `utils/metadata.py` | datacenter, ri_id, node_id, vm_id, host, site_id, timestamp, extra |

All three represent the same concept (ingested file metadata) with slightly different field names and types. `ingest_any.py` and `partner_payload.py` even use the same class name `PartnerMeta`.

---

### 2.3 Duplicated MetricSourceMap Upsert

The `metric_source_map` upsert is performed in **two places**:

1. [insert_metric_sample.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/services/insert_metric_sample.py#L56-L70) (L56–70)
2. [mapping_registry.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/registry/mapping_registry.py#L54-L68) (L54–68)

Both run during `process_metric_sample()`, causing **two separate DB round-trips** for the same upsert.

---

### 2.4 Duplicated insert_metric_definition Calls

During the Streamlit uploader flow:
1. `process_metric_sample()` → `insert_mapped_metric()` — creates/updates MetricDefinition
2. After the loop, `insert_metric_definition()` is called **again** for each unified key

This causes duplicate insert attempts (caught by IntegrityError, but noisy).

---

### 2.5 `_tokens()` and `_norm()` Duplicated 6+ Times

The regex `re.compile(r"[A-Z]?[a-z]+|[0-9]+")` and its `_tokens()`/`_norm()` helpers are defined in:
- `alias_classifier.py`
- `ensemble_classifier.py`
- `fallbacks.py`
- `automated_mapper.py`
- `ingest_any.py`
- `partner_payload.py`

---

### 2.6 No Alembic Migrations

Despite `alembic` being listed as a dev dependency in `pyproject.toml`, there is:
- No `alembic.ini`
- No `migrations/` directory
- No version tracking

Schema changes require `create_schema.py` (creates-all) or raw SQL scripts. No rollback capability.

---

## 3. Configuration Issues

### 3.1 Multiple `.env` Files

| File | Content | Used By |
|------|---------|---------|
| `.env` (root) | PostgreSQL, InfluxDB, mapping path, debug flag | `config.py` (pydantic-settings) |
| `cloud_metrics/utils/.env` | `DATABASE_URL=sqlite:///./test.db` | **Stale** — overrides root .env if CWD is utils/ |

### 3.2 Mapping Path Confusion

Three different ways to resolve the mapping JSON path:
1. `config.py`: `METRIC_MAPPING_JSON_PATH` env var → fallback `cloud_metrics/data/metric_mapping.json`
2. `mapping_sync.py`: `MAPPING_JSON_PATH` env var → fallback `cloud_metrics/mapping/metric_mapping.json`
3. `rebuild_mapping_json.py`: `METRIC_MAPPING_JSON_PATH` or `CLOUD_METRICS_MAPPING_PATH` → fallback `cloud_metrics/data/metric_mapping.json`

Different env var names, different fallback paths.

### 3.3 Docker Compose Port Issues

- PostgreSQL: maps `5433:5433` but container listens on `5432` (wrong internal port)
- InfluxDB: maps port `80` but `.env` uses `8086`
- No data volumes — data is lost on container restart

### 3.4 Credentials in Source Control

- `.env` contains real InfluxDB token and PostgreSQL password
- `docker-compose.yml` has hardcoded credentials
- Should use `.env.sample` pattern (which exists but is incomplete)

---

## 4. Code Quality Issues

### 4.1 `sys.path.insert(0, ...)` in Model Files

Multiple model files modify `sys.path` at import time:
- `datacenter.py`, `metric_definition.py`, `metric_keyword.py`, `namespace_models.py`, `upload_log.py`

```python
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
```

This is fragile and should be handled by proper package installation.

### 4.2 Bare `except` Clauses

Multiple places catch all exceptions silently:
- `automated_mapper.py`: L161–163, L178, L196–197, L210–213, L243–244
- `mapping_sync.py`: L37, L56–57
- `ensemble_classifier.py`: L95

### 4.3 Commented-Out Code

**Massive** blocks of commented-out code:
- `streamlit_uploader.py`: Lines 224–493 (~270 lines, ~55% of file)
- `external_json.py`: Lines 117–142
- `ingest_any.py`: Lines 261–283
- `backfill_standards.py`: Lines 9–23

### 4.4 Deprecated API Usage

```python
# db_models.py
from sqlalchemy.ext.declarative import declarative_base  # Deprecated since SQLAlchemy 1.4
```

Should use `from sqlalchemy.orm import DeclarativeBase`.

### 4.5 `datetime.utcnow()` Usage

Used throughout the codebase (15+ locations). This is deprecated since Python 3.12 and returns naive datetimes that can cause timezone issues. Should use `datetime.now(timezone.utc)`.

---

## 5. Test Coverage Gaps

### 5.1 Test Status

| Test File | Tests | Status | Notes |
|-----------|-------|--------|-------|
| `test_api_endpoints.py` | 4 | ✅ Likely passing | Uses monkeypatch, no DB |
| `test_influx_service.py` | 1 | ⚠️ May fail | References `settings.INFLUX_BUCKET` directly |
| `test_namespace_mapper.py` | 3 | ❌ Broken | Expects old keys `CPUUtilization`→`cpu_usage` that no longer exist in mapping |
| `test_sql_service.py` | 1 | ❌ Broken | Imports `cloud_metrics.services.sql_service` which does not exist |

### 5.2 Missing Test Coverage

| Component | Files | Tests |
|-----------|-------|-------|
| Ensemble classifier | `ensemble_classifier.py` | **None** |
| Alias classifier | `alias_classifier.py` | **None** |
| Semantic classifier | `semantic_classifier.py` | **None** |
| Fallback classifier | `fallbacks.py` | **None** |
| Automated mapper | `automated_mapper.py` | **None** |
| File parsers | `structured_parser.py`, `unstructured_parser.py` | **None** |
| Universal loader | `ingest_any.py` | **None** |
| Namespace registry | `namespace_registry.py` | **None** |
| Mapping registry | `mapping_registry.py` | **None** |
| Standards registry | `standards_registry.py` | **None** |
| All service layer | `insert_*.py`, `keyword_learning.py` | **None** |
| Unified key normalization | `unified_key.py` | **None** |
| Mapping sync | `mapping_sync.py` | **None** |
| Export logic | `external_json.py`, `rebuild_mapping_json.py` | **None** |

**Effective test coverage: ~5%** (only API endpoints and a partial InfluxDB write test).

---

## 6. Refactoring Risks

### 6.1 High-Risk Changes

| Change | Risk | Reason |
|--------|------|--------|
| Refactoring classification pipeline | 🔴 High | Multiple callers, two parallel implementations, auto-learning side effects |
| Changing unified_key format | 🔴 High | Keys are stored in 4+ tables + InfluxDB + JSON files; no migration tool |
| Modifying metric_mapping.json schema | 🔴 High | Read by namespace_mapper with LRU cache; sync'd by mapping_sync; rebuilt by exporter |
| Changing DB schema | 🟡 Medium | No Alembic migrations; require manual DDL or full recreate |
| Consolidating PartnerMeta classes | 🟡 Medium | Three variants used in different code paths; need to trace all callers |

### 6.2 Moderate-Risk Changes

| Change | Risk | Reason |
|--------|------|--------|
| Removing dead code | 🟢 Low | Only need to verify no imports reference removed functions |
| Adding new classifiers | 🟢 Low | Ensemble pattern is extensible; add before fallback |
| Adding new parsers | 🟢 Low | `ingest_any.py` has clear extension points |
| Fixing Docker ports | 🟢 Low | Config-only change |
| Adding tests | 🟢 Low | No side effects; existing code is testable with monkeypatching |

---

## 7. Summary Dashboard

| Dimension | Score | Details |
|-----------|-------|---------|
| **Code Duplication** | 🔴 High | Classification rules ×2, MetricSourceMap upsert ×2, PartnerMeta ×3, _tokens() ×6 |
| **Dead Code** | 🟡 Medium | fallbacks.py L21–50, streamlit_uploader.py ~270 lines, unused DB models |
| **Test Coverage** | 🔴 Critical | ~5% coverage; 2 of 4 test files broken; zero classifier/parser/service tests |
| **Configuration** | 🟡 Medium | Multiple .env files, inconsistent mapping paths, Docker port issues |
| **Security** | 🟡 Medium | Credentials in source control, no auth on API endpoints |
| **Schema Management** | 🔴 High | No migrations, inconsistent DDL sources (ORM vs SQL scripts) |
| **Documentation** | 🟢 Improving | README is minimal but inline docstrings are decent |
| **Architecture** | 🟡 Medium | Good separation of concerns but too many parallel paths for same functionality |
| **Error Handling** | 🟡 Medium | Many bare excepts; errors logged but not surfaced to callers |
| **Maintainability** | 🟡 Medium | Clear module boundaries but high coupling between services |
