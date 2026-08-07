# Registry-Driven CIM Architecture: Database Migration Plan

This document details the database schema transitions, table deprecations, data porting strategies, and migration safeguards for the registry-driven CIM.

> **Milestone 2 update (2026-08-03):** An additive `cim_*` schema was introduced (revision `c2f8a1b9e047`). It does **not** replace or drop the Antigravity-era tables described in §1 below. See [REGISTRY_DATABASE_MODEL.md](REGISTRY_DATABASE_MODEL.md) and [REGISTRY_SCHEMA_REFERENCE.md](REGISTRY_SCHEMA_REFERENCE.md).

---

## 0. Milestone 2 Additive Schema (CURRENT)

### 0.1 Revision

| Item | Value |
|------|-------|
| Alembic revision | `c2f8a1b9e047` |
| Revises | `a7708d6bee50` |
| File | `migrations/versions/c2f8a1b9e047_add_cim_registry_tables.py` |
| ORM | `cloud_metrics/models/cim_registry.py` |
| Tests | `tests/test_cim_registry_migration.py` |

### 0.2 Tables created

`cim_quantity_kinds`, `cim_units`, `cim_sources`, `cim_assets`, `cim_standards`, `cim_standard_terms`, `cim_metric_definitions`, `cim_metric_mappings`, `cim_lifecycle_stages`, `cim_metric_lifecycle_links`, `cim_validation_rules`, `cim_evidence_requirements`, `cim_provenance_records`, `cim_extension_metrics`

### 0.3 Rollback strategy

```bash
# Apply Milestone 2 (after prior revisions are present on the target DB)
alembic upgrade c2f8a1b9e047

# Roll back Milestone 2 only (drops all cim_* tables created by this revision)
alembic downgrade a7708d6bee50
```

Downgrade drops Milestone 2 tables in reverse dependency order and removes their indexes. Legacy / Antigravity tables are unaffected.

**Operations:** see the staging/production runbook [POSTGRES_MIGRATION_RUNBOOK.md](../deployment/POSTGRES_MIGRATION_RUNBOOK.md) (Milestone 11).

### 0.4 Out of scope for Milestone 2

* Migrating rows from `metric_definitions` / `cim_mappings` / etc. into `cim_*` tables
* Seeding full registry catalogues
* Changing ingestion / classifier / API runtime paths
* Dropping or renaming old tables

### 0.5 Validation

Isolated SQLite tests in `tests/test_cim_registry_migration.py` verify:

* upgrade creates all 14 tables with required columns
* downgrade removes them
* uniqueness constraints (namespace, symbol, quantity kind name, source name+type, lifecycle stage name)
* multiple lifecycle links and multiple standards mappings per metric
* legacy model tables remain registered on `Base.metadata`

---

## 1. Target Database Schemas (Antigravity-era — retained)

### 1.1 Core Registry Tables (NEW at the time)

#### `quantity_kinds`
* Identifies the category of physical dimension being measured.
```sql
CREATE TABLE quantity_kinds (
    id SERIAL PRIMARY KEY,
    name VARCHAR(128) NOT NULL UNIQUE,  -- e.g. Energy, Power, DataSize, Temperature, Percentage, Time
    description VARCHAR(512) NULL,
    qudt_uri VARCHAR(256) NULL          -- Link to QUDT vocabulary
);
```

#### `units`
* Stores specific units, linking them to a `quantity_kind` and configuring conversion offsets and factors.
```sql
CREATE TABLE units (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(64) NOT NULL UNIQUE, -- e.g. Wh, kWh, W, kW, °C, GB, B
    name VARCHAR(128) NOT NULL,          -- e.g. watt-hour, kilowatt-hour
    quantity_kind_id INTEGER NOT NULL REFERENCES quantity_kinds(id),
    si_base BOOLEAN NOT NULL DEFAULT FALSE,
    canonical_unit_id INTEGER NULL REFERENCES units(id),
    conversion_factor DOUBLE PRECISION NOT NULL DEFAULT 1.0,
    conversion_offset DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    qudt_uri VARCHAR(256) NULL,
    saref_uri VARCHAR(256) NULL
);
```

#### `sources`
* Identifies metric source origins and protocols.
```sql
CREATE TABLE sources (
    id SERIAL PRIMARY KEY,
    name VARCHAR(128) NOT NULL UNIQUE,  -- e.g. "aws_cloudwatch", "scaphandre", "file_upload"
    type VARCHAR(64) NOT NULL,          -- file, api, prometheus, opentelemetry, scaphandre, manual
    protocol VARCHAR(64) NULL,          -- HTTP, gRPC, file, MQTT
    format VARCHAR(64) NULL,            -- JSON, YAML, CSV, XML, Prometheus, OTLP
    schema_version VARCHAR(64) NULL,
    capabilities JSON DEFAULT '{}',
    auth_method VARCHAR(64) NOT NULL DEFAULT 'none',
    status VARCHAR(64) NOT NULL DEFAULT 'active',
    metadata_info JSON DEFAULT '{}',    -- Avoid 'metadata' keyword collision
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);
```

#### `assets`
* Models infrastructure elements in a parent-child hierarchy.
```sql
CREATE TABLE assets (
    id SERIAL PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    type VARCHAR(64) NOT NULL,          -- datacenter, node, vm, container, server, cpu
    parent_id INTEGER NULL REFERENCES assets(id),
    location VARCHAR(256) NULL,
    provider VARCHAR(128) NULL,
    specifications JSON DEFAULT '{}',
    lifecycle_stage_id INTEGER NULL,
    status VARCHAR(64) NOT NULL DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);
```

#### `cim_mappings`
* Core mapping table linking raw keys to canonical CIM definitions and standards.
```sql
CREATE TABLE cim_mappings (
    id SERIAL PRIMARY KEY,
    source_key VARCHAR(255) NOT NULL,
    source_id INTEGER NULL REFERENCES sources(id),
    cim_metric_id INTEGER NOT NULL REFERENCES metric_definitions(id),
    standard_id INTEGER NULL REFERENCES standards(id),
    relation_type VARCHAR(64) NOT NULL DEFAULT 'underReview', -- exactMatch, closeMatch, etc.
    confidence DOUBLE PRECISION NOT NULL DEFAULT 1.0,
    rationale TEXT NULL,
    approved_by VARCHAR(128) NULL,
    approved_at TIMESTAMP WITH TIME ZONE NULL,
    status VARCHAR(64) NOT NULL DEFAULT 'proposed',          -- proposed, approved, rejected
    version INTEGER NOT NULL DEFAULT 1,
    origin VARCHAR(64) NOT NULL DEFAULT 'manual',            -- manual, auto-learned, seeded
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);
CREATE INDEX idx_cim_mappings_source_key ON cim_mappings(source_key);
```

#### `provenance_records`
* Stores full lineage auditing logs.
```sql
CREATE TABLE provenance_records (
    id SERIAL PRIMARY KEY,
    entity_type VARCHAR(64) NOT NULL,   -- metric_sample, cim_mapping
    entity_id INTEGER NULL,
    activity VARCHAR(64) NOT NULL,      -- ingestion, classification, unit_conversion
    agent VARCHAR(128) NOT NULL,
    started_at TIMESTAMP WITH TIME ZONE NULL,
    ended_at TIMESTAMP WITH TIME ZONE NULL,
    inputs JSON DEFAULT '{}',
    outputs JSON DEFAULT '{}',
    method VARCHAR(128) NULL,
    confidence DOUBLE PRECISION NULL,
    prov_uri VARCHAR(256) NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);
```

---

## 2. Updates to Existing Tables

### `metric_definitions` (MODIFIED)
To align with the Metric Registry requirements, the existing `metric_definitions` table is modified to incorporate canonical fields:
```sql
ALTER TABLE metric_definitions ADD COLUMN label VARCHAR(255) NULL;
ALTER TABLE metric_definitions ADD COLUMN description TEXT NULL;
ALTER TABLE metric_definitions ADD COLUMN domain VARCHAR(64) NULL;
ALTER TABLE metric_definitions ADD COLUMN quantity_kind_id INTEGER NULL REFERENCES quantity_kinds(id);
ALTER TABLE metric_definitions ADD COLUMN canonical_unit_id INTEGER NULL REFERENCES units(id);
ALTER TABLE metric_definitions ADD COLUMN metric_type VARCHAR(64) DEFAULT 'observed' NOT NULL;
ALTER TABLE metric_definitions ADD COLUMN status VARCHAR(64) DEFAULT 'active' NOT NULL;
ALTER TABLE metric_definitions ADD COLUMN version INTEGER DEFAULT 1 NOT NULL;
ALTER TABLE metric_definitions ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL;
```

---

## 3. Deprecated and Removed Tables

The following legacy tables were dropped in revision `a7708d6bee50` (Antigravity). Milestone 2 does **not** drop further tables:

1. **`metric_keywords`**: Replaced conceptually by mapping registry entries (`origin='auto-learned'`).
2. **`metric_source_map`**: Replaced conceptually by mapping registry entries.

---

## 4. Alembic Migration Strategy & Constraints

### 4.1 Constraint Naming Rule
To prevent errors when running migrations across multiple DBMS engines (e.g. SQLite for unit tests and PostgreSQL for production), we enforce explicit, standard naming conventions for all constraints and foreign keys. This guarantees that Alembic can properly drop or alter constraints during downgrades without raising `CompileError`.
The naming convention is defined in Alembic's `env.py` and models:
* Foreign Keys: `fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s`
* Unique constraints: `uq_%(table_name)s_%(column_0_name)s`
* Indexes: `ix_%(table_name)s_%(column_0_name)s`

Milestone 2 follows this pattern with explicit names on every FK / unique / index.

### 4.2 SQLite Batch Mode Workaround
SQLite does not natively support many standard `ALTER TABLE` operations (such as adding foreign keys, dropping columns, or modifying column constraints). In migrations targeting SQLite, Alembic must be configured to run in **batch mode**:
```python
with op.batch_alter_table('metric_definitions', render_as_batch=True) as batch_op:
    batch_op.add_column(sa.Column('label', sa.String(length=255), nullable=True))
    batch_op.create_foreign_key(
        'fk_metric_definitions_canonical_unit_id_units',
        'units', ['canonical_unit_id'], ['id']
    )
```

Milestone 2 only `CREATE TABLE` / `DROP TABLE`, so batch mode is not required for revision `c2f8a1b9e047`.

---

## 5. Data Porting Logic

Data migration is handled sequentially by `cloud_metrics/scripts/migrate_existing_data.py` (planned / Antigravity). **Not executed in Milestone 2.**

Future steps (later milestone):
1. **Assets**: Datacenters → `cim_assets` (`type='datacenter'`).
2. **Metrics**: Port / dual-write `metric_definitions` → `cim_metric_definitions`.
3. **Mappings**: Port `cim_mappings` / legacy maps → `cim_metric_mappings`.
4. **Standards / units / sources**: Seed and align catalogues into `cim_*` tables.

---

## 6. Migration Chain (current)

```
58e138959809  initial_schema
    → 45460b743918  add_registries_and_expand_metric
        → 270d7d8ed609  add_provenance_records
            → a7708d6bee50  drop_legacy_tables
                → c2f8a1b9e047  add_cim_registry_tables   ← Milestone 2
```
