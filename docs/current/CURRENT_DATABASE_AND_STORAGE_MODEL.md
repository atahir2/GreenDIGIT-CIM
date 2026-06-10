# Current Database & Storage Model — GreenDIGIT CIM

> **Generated**: 2026-06-10 · **Scope**: Full storage audit (read-only)

---

## 1. Storage Architecture Overview

The system uses a **three-tier storage architecture**:

| Tier | Technology | Purpose | Connection |
|------|-----------|---------|------------|
| **Relational** | PostgreSQL 15 | Metadata, taxonomy, mappings, samples, audit | SQLAlchemy 2.0 via `DATABASE_URL` |
| **Time-Series** | InfluxDB 2.7.11 | Metric values for range queries | influxdb-client via `INFLUX_*` env vars |
| **File-Based** | JSON files on disk | Mapping cache, export artifacts | Direct file I/O |

```mermaid
graph LR
    subgraph "PostgreSQL (11 tables)"
        T1["datacenters"]
        T2["metric_definitions"]
        T3["metric_samples"]
        T4["metric_keywords"]
        T5["metric_mappings"]
        T6["mapping_proposals"]
        T7["mapping_events"]
        T8["metric_source_map"]
        T9["standards"]
        T10["categories"]
        T11["subcategories"]
        T12["metric_standard_map"]
        T13["file_upload_logs"]
    end

    subgraph "InfluxDB"
        B1["Bucket: cloud_metrics"]
    end

    subgraph "File System"
        F1["mapping/metric_mapping.json"]
        F2["data/metric_mapping.json"]
        F3["data/exports/*.json"]
        F4["output/*.json"]
    end
```

---

## 2. PostgreSQL Schema (Detail)

### 2.1 Connection Configuration

**File**: [config.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/utils/config.py)

```python
DATABASE_URL = "postgresql+psycopg2://postgres:admin123@localhost:5433/cloud_metrics"
_engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=_engine, autocommit=False, autoflush=False, future=True)
```

- Uses `psycopg2` driver
- Connection pool with pre-ping health checks
- Non-default port: **5433** (standard PostgreSQL is 5432)

### 2.2 Schema Creation

**Two mechanisms** (potentially inconsistent):

1. **SQLAlchemy ORM** — `scripts/create_schema.py` runs `Base.metadata.create_all()`
2. **Raw SQL** — `sql_scripts/namespace_schema.sql` defines DDL manually

**No migration system** (Alembic is listed as a dev dependency but not configured).

---

### 2.3 Table: `datacenters`

**Model**: [datacenter.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/models/datacenter.py)

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PK, autoincrement | |
| `name` | VARCHAR(255) | NOT NULL, UNIQUE | Datacenter identifier |
| `location` | VARCHAR(255) | nullable | Physical location |
| `provider` | VARCHAR(255) | nullable | Cloud/grid provider |
| `created_at` | TIMESTAMP(tz) | server_default=now() | |

**Relationships**: `upload_logs` (one-to-many → FileUploadLog)

**Usage**: Created by `get_or_create_datacenter_id()` or `insert_datacenter()`. Name comes from file metadata or user input.

---

### 2.4 Table: `metric_definitions`

**Model**: [metric_definition.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/models/metric_definition.py)

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PK, autoincrement | |
| `unified_key` | VARCHAR(255) | NOT NULL, UNIQUE | e.g., `gd.energy.consumption.total` |
| `tags` | JSON | nullable | Classification tags `["energy","consumption","total"]` |
| `sources` | JSON | nullable | Source file/datacenter names |
| `created_at` | TIMESTAMP(tz) | server_default=now() | |

**Relationships**: `standards` (many-to-many via `metric_standard_map`)

**Issue**: `sources` stores **datacenter names** (e.g., "datacenter_A"), not raw metric keys. This is by design in `insert_mapped_metric()` which passes `origin` as source.

---

### 2.5 Table: `metric_samples`

**Model**: [metric_sample.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/models/metric_sample.py)

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PK, autoincrement | |
| `datacenter_id` | INTEGER | FK→datacenters.id, NOT NULL, indexed | |
| `unified_key` | VARCHAR(255) | NOT NULL, indexed | Classified metric key |
| `raw_key` | VARCHAR(255) | NOT NULL | Original partner metric name |
| `value` | FLOAT | NOT NULL | Metric value |
| `unit` | VARCHAR(64) | nullable | Inferred unit (kwh, w, bytes, etc.) |
| `tags` | JSON | NOT NULL, default='{}' | Extra sample tags |
| `source_file` | VARCHAR(512) | nullable | Origin filename |
| `captured_at` | TIMESTAMP(tz) | NOT NULL | When the metric was observed |
| `created_at` | TIMESTAMP(tz) | server_default=now(), NOT NULL | When the row was inserted |
| `ri_id` | VARCHAR(128) | nullable | Research Infrastructure ID |
| `node_id` | VARCHAR(128) | nullable | Node identifier |
| `vm_id` | VARCHAR(128) | nullable | Virtual Machine ID |
| `host` | VARCHAR(256) | nullable | Hostname |
| `site_id` | VARCHAR(256) | nullable | Composite site identifier |
| `clf_confidence` | FLOAT | nullable | Classification confidence (0–1) |
| `clf_rationale` | TEXT | nullable | Classification rationale string |
| `domain` | TEXT | nullable | Domain hint: cloud/grid/network |
| `extra_meta` | JSONB | NOT NULL, default='{}' | Partner-specific extra metadata |

**This is the primary observation table** — one row per (metric, timestamp, datacenter) tuple. It is the most data-intensive table in the system.

---

### 2.6 Table: `metric_keywords`

**Model**: [metric_keyword.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/models/metric_keyword.py)

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PK, autoincrement | |
| `keyword` | VARCHAR(255) | NOT NULL, UNIQUE | Normalized raw key |
| `category` | VARCHAR(255) | nullable | Learned category |
| `subcategory` | VARCHAR(255) | nullable | Learned subcategory |
| `short_key` | VARCHAR(255) | nullable | Learned short key |
| `source_key` | VARCHAR(255) | nullable | Original raw key form |
| `created_at` | TIMESTAMP(tz) | server_default=now() | |

**Purpose**: Auto-learning cache. When a raw key is classified with confidence ≥ 0.85, a row is stored here for instant O(1) lookup next time.

**Issue**: The `keyword_learning.py` sets `mk.updated_at = datetime.utcnow()` but the model has no `updated_at` column — this silently sets an unmapped attribute.

---

### 2.7 Tables: `metric_mappings`, `mapping_proposals`, `mapping_events`

**Model**: [metric_mapping.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/models/metric_mapping.py)

#### `metric_mappings` — Canonical Approved Mappings

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | INTEGER | PK |
| `raw_key` | VARCHAR(255) | NOT NULL, UNIQUE, indexed |
| `unified_key` | VARCHAR(255) | NOT NULL, indexed |
| `version` | INTEGER | NOT NULL, default=1 |
| `unit` | VARCHAR(64) | nullable |
| `tags` | JSON | nullable |
| `approved_at` | TIMESTAMP(tz) | server_default=now() |

#### `mapping_proposals` — Pending Review

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | INTEGER | PK |
| `raw_key` | VARCHAR(255) | NOT NULL, indexed |
| `suggested_unified_key` | VARCHAR(255) | NOT NULL |
| `confidence` | FLOAT | NOT NULL |
| `rationale` | VARCHAR(1024) | nullable |
| `unit` | VARCHAR(64) | nullable |
| `tags` | JSON | nullable |
| `status` | ENUM(PROPOSED/APPROVED/REJECTED) | NOT NULL, default=PROPOSED |
| `created_at` | TIMESTAMP(tz) | server_default=now() |

#### `mapping_events` — Audit Trail

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | INTEGER | PK |
| `raw_key` | VARCHAR(255) | NOT NULL, indexed |
| `event` | VARCHAR(64) | NOT NULL (PROPOSED/APPROVED/REJECTED/UPDATED) |
| `payload` | JSON | nullable |
| `created_at` | TIMESTAMP(tz) | server_default=now() |

**Status**: All three tables have models defined but **no code writes to them**. The `registry_service.py` reads from `metric_mappings` but the table is never populated. The proposal/event audit trail is entirely inactive.

---

### 2.8 Table: `metric_source_map`

**Model**: [metric_source_map.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/models/metric_source_map.py)

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | INTEGER | PK |
| `datacenter_id` | INTEGER | FK→datacenters.id, NOT NULL |
| `raw_key` | VARCHAR(255) | NOT NULL |
| `unified_key` | VARCHAR(255) | NOT NULL |
| `first_seen` | TIMESTAMP(tz) | server_default=now() |
| `last_seen` | TIMESTAMP(tz) | server_default=now(), onupdate=now() |

**Unique constraint**: `(datacenter_id, raw_key)`

**Purpose**: Per-datacenter tracking of which raw keys have been seen and what they map to. Written by both `insert_metric_sample()` and `register_mapping()` — **duplicated upsert logic**.

---

### 2.9 Tables: `standards`, `metric_standard_map`

**Model**: [standard_models.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/models/standard_models.py)

#### `standards`

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | INTEGER | PK |
| `code` | TEXT | UNIQUE, NOT NULL (e.g., "TGG-PUE", "ISO-50001") |
| `name` | TEXT | NOT NULL |
| `url` | TEXT | nullable |
| `description` | TEXT | nullable |

#### `metric_standard_map`

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | INTEGER | PK |
| `metric_definition_id` | INTEGER | FK→metric_definitions.id, ON DELETE CASCADE |
| `standard_id` | INTEGER | FK→standards.id, ON DELETE CASCADE |
| `standard_metric_code` | TEXT | nullable (e.g., "PUE", "WUE") |
| `confidence` | FLOAT | nullable (0–1) |
| `rationale` | TEXT | nullable |

**Unique constraint**: `(metric_definition_id, standard_id)`

---

### 2.10 Tables: `categories`, `subcategories`

**Model**: [namespace_models.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/models/namespace_models.py)

#### `categories`

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | INTEGER | PK |
| `name` | VARCHAR(100) | UNIQUE, NOT NULL |
| `description` | TEXT | nullable |
| `standard_id` | INTEGER | FK→standards.id, ON DELETE SET NULL, nullable |

#### `subcategories`

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | INTEGER | PK |
| `name` | VARCHAR(100) | NOT NULL |
| `category_id` | INTEGER | FK→categories.id, NOT NULL |
| `description` | TEXT | nullable |

**Relationship**: `Category` ←→ `Subcategory` (one-to-many with cascade delete)

---

### 2.11 Table: `file_upload_logs`

**Model**: [upload_log.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/models/upload_log.py)

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | INTEGER | PK |
| `filename` | VARCHAR(512) | NOT NULL |
| `datacenter_id` | INTEGER | FK→datacenters.id, ON DELETE CASCADE |
| `uploaded_by` | VARCHAR(255) | nullable |
| `uploaded_at` | TIMESTAMP(tz) | server_default=now() |

---

## 3. InfluxDB Configuration

**File**: [influx_service.py](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/services/influx_service.py)

| Setting | Value |
|---------|-------|
| URL | `http://localhost:8086` |
| Org | `UvA` |
| Bucket | `cloud_metrics` |
| Write Precision | Nanoseconds |
| Write Mode | Synchronous |
| Client | `influxdb_client.InfluxDBClient` |

### Data Model in InfluxDB

```
Measurement: unified_key (e.g., "gd.energy.consumption.total")
  Fields:
    value: float
  Tags:
    (optional, passed from metric tags dict)
  Timestamp:
    captured_at or datetime.utcnow()
```

### Query Interface

```python
# Flux query construction
from(bucket: "cloud_metrics")
  |> range(start: -1h, stop: now())
  |> filter(fn: (r) => r._measurement == "gd.energy.consumption.total")
  |> filter(fn: (r) => r["region"] == "eu-west")
```

Returns pandas DataFrame converted to `list[dict]`.

**Issue**: `query_metrics()` returns `df.to_dict(orient="records")` which requires pandas — not listed as a direct dependency (comes transitive via influxdb-client).

---

## 4. File-Based Storage

### 4.1 Runtime Mapping File

**Path**: `cloud_metrics/mapping/metric_mapping.json`

**Schema**: `{ unified_key: [source_key_1, source_key_2, ...] }`

**Updated by**: `mapping_sync.py` via `sync_metric_mapping()`

**Read by**: `namespace_mapper.py` via `_load_mapping()` (LRU-cached)

**Issues**:
- Source keys mix datacenter names with actual raw metric keys
- Contains `gd.uncategorized.unknown.unknown` bucket with many entries
- Single-writer assumption (no locking for concurrent processes)

### 4.2 Exported Mapping File

**Path**: `cloud_metrics/data/metric_mapping.json`

**Schema**:
```json
{
  "generated_at": "ISO timestamp",
  "count": N,
  "mappings": {
    "raw_key": { "unified_key": "gd.x.y.z", "last_seen": "ISO timestamp" }
  }
}
```

**Updated by**: `exporters/rebuild_mapping_json.py` via `rebuild_mapping()`

### 4.3 Partner Export Files

**Path**: `cloud_metrics/data/exports/{basename}_unified.json`

**Schema**:
```json
{
  "metadata": { "site_id": "...", "datacenter": "...", "timestamp": "...", ... },
  "metrics": { "gd.x.y.z": value, ... }
}
```

### 4.4 Legacy Output Files

**Path**: `output/{site_id}_{timestamp}.json`

32 files from previous ingestion runs. Contain similar structure to partner exports.

---

## 5. Session Management Patterns

The codebase uses **inconsistent** session management patterns:

| Pattern | Files Using It | Safety |
|---------|---------------|--------|
| `with SessionLocal() as s:` (context manager) | config.py, insert_mapped_metric.py, insert_metric_sample.py, namespace_registry.py, mapping_registry.py, keyword_learning.py, standards_registry.py | ✅ Safe — auto-closes |
| `session = SessionLocal(); try/finally: session.close()` | insert_datacenter.py, insert_file_upload_log.py, insert_metric_definition.py, namespace_generator.py | ⚠️ Verbose but safe |
| `session = SessionLocal(); try/finally: session.close()` with no rollback on generic exception | automated_mapper.py (L66–76) | ❌ Potentially unsafe — session left in bad state |

---

## 6. Docker Compose Setup

**File**: [docker-compose.yml](file:///z:/GreenDIGIT_CIM_testing_v1/cloud_metrics/docker-compose.yml)

```yaml
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: admin123
      POSTGRES_DB: cloud_metrics
    ports: ["5433:5433"]       # ⚠️ Maps 5433→5433, but PostgreSQL defaults to 5432 inside container

  influxdb:
    image: influxdb:2.7.11
    environment:
      DOCKER_INFLUXDB_INIT_ORG: UvA
      DOCKER_INFLUXDB_INIT_BUCKET: cloud_metrics
    ports: ["80"]              # ⚠️ Maps port 80, not 8086 (Influx default)
```

**Issues**:
- PostgreSQL port mapping `5433:5433` is wrong — container listens on 5432 internally
- InfluxDB port maps 80, but `.env` uses 8086
- Password `admin123` is hardcoded
- No volume mounts for data persistence
