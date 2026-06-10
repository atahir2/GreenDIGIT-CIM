# GreenDIGIT Common Information Model (CIM) Registry Service

A robust, modular, registry-driven Common Information Model (CIM) for cloud metrics. This project transitions fragmented, file-based mapping configuration logic into a centralized, database-backed registry service that governs metric naming, unit validation, source protocols, infrastructure assets, and compliance standards.

---

## 1. Architecture Overview

The target CIM is designed around **11 core registries** to enforce schema governance, validate telemetry data, normalize units, and record audit trails:

```mermaid
graph TB
    subgraph "Core Registries"
        MR["1. Metric Registry<br/>(CIM Metric Definitions)"]
        UR["2. Unit Registry<br/>(Quantity Kinds + Conversions)"]
        SR["3. Source Registry<br/>(Telemetry Origins)"]
        AR["4. Asset Registry<br/>(Infrastructure Hierarchy)"]
    end

    subgraph "Alignment Registries"
        STR["5. Standards Registry<br/>(External Vocabularies)"]
        MPR["6. Mapping Registry<br/>(Key Translation & Mappings)"]
    end

    subgraph "Governance Registries"
        LR["7. Lifecycle Registry<br/>(RI Stage Association)"]
        RR["8. Rule Registry<br/>(Validation Constraints)"]
        ER["9. Evidence Registry<br/>(Compliance Auditing)"]
    end

    subgraph "Operational Registries"
        PR["10. Provenance Registry<br/>(Data Lineage Audits)"]
        XR["11. Extension Registry<br/>(Unstandardized Metrics)"]
    end

    MR --> UR
    MR --> STR
    MR --> LR
    SR --> MR
    AR --> MR
    MPR --> MR
    MPR --> STR
    MPR --> SR
    RR --> MR
    RR --> UR
    ER --> MR
    ER --> STR
    PR --> MR
    PR --> MPR
    PR --> SR
    XR --> MR
    XR --> STR
```

### Registry Breakdown
1. **Metric Registry**: Stores controlled CIM definitions, namespaces, domains, categories, subcategories, canonical units, and status.
2. **Unit Registry**: Stores units, quantity kinds, conversion factors, offsets, and QUDT/SAREF alignment.
3. **Source Registry**: Registers metric origins (Prometheus, OpenTelemetry, APIs, files, Scaphandre) and credentials.
4. **Asset Registry**: Models infrastructure parent-child trees (Datacenter → Cluster → Node → Server → CPU/GPU/VM).
5. **Standards Registry**: Evaluates external compliance frameworks (ISO 50001, SAREF, QUDT, OTel SemConv, SSN).
6. **Mapping Registry**: Unified database links between raw source telemetry keys and canonical CIM definitions with confidence thresholds and relation types (`exactMatch`, `closeMatch`, `broadMatch`, etc.).
7. **Lifecycle Registry**: Links assets and metrics to Research Infrastructure stages (planning, operation, decommission).
8. **Rule Registry**: Validates values and constraints (e.g., PUE must be $\ge 1.0$, percentage bounds).
9. **Evidence Registry**: Maps metrics to reporting requirements for certification readiness.
10. **Provenance Registry**: Audit records logging the origin, normalization method, and validation outcomes for telemetry ingestion.
11. **Extension Registry**: Handles candidate metrics that fall outside established standards.

---

## 2. System Logic & Module Interconnection Flow

The flowchart below demonstrates the path of telemetry data ingestion, mapping resolution, unit normalization, rule validation, and database auditing, as well as developer/user API access:

```mermaid
flowchart TD
    %% Telemetry Sources
    subgraph Sources ["Telemetry Ingestion Streams"]
        A1["AWS CloudWatch JSON"] 
        A2["GCP Monitoring JSON"] 
        A3["Prometheus Scraping"]
        A4["File Upload (JSON/YAML/CSV/XML)"]
    end

    %% Ingestion Pipeline & Parsers
    subgraph Ingestion ["Ingestion & Parsing Services"]
        B1["realtime_ingestor.py / unified_ingestion.py"]
        B2["structured_parser.py / unstructured_parser.py"]
        B3["automated_mapper.py (process_metric_sample)"]
    end

    %% Mapping & Classification Engine
    subgraph Classification ["Classification & Mapping Resolution"]
        C1["ensemble_classifier.py (classify_metric)"]
        C2["mapping_registry_service.py (resolve_mapping)"]
        C3["Database Table: cim_mappings"]
        C4["Fallback Classifiers (Fuzzy/Embedding matching)"]
    end

    %% Normalization & Rules
    subgraph Governance ["Unit Normalization & Validation Rules"]
        D1["unit_registry_service.py (convert_value)"]
        D2["Database Tables: quantity_kinds & units"]
        D3["rule_registry_service.py (validate_metric_sample)"]
    end

    %% Auditing & Lineage
    subgraph Auditing ["Data Lineage & Provenance"]
        E1["provenance_registry_service.py (record_activity)"]
        E2["Database Table: provenance_records"]
    end

    %% Persistence
    subgraph Storage ["Persistent Storage Stores"]
        F1[("PostgreSQL DB (Metadata, Mappings, Lineage)")]
        F2[("InfluxDB (Metric Samples Time-Series)")]
    end

    %% APIs and Dashboards
    subgraph Interface ["Client APIs & User Interfaces"]
        G1["registry_api.py (FastAPI Routes /api/v1/registry/*)"]
        G2["admin_panel.py (Streamlit Admin Dashboard)"]
        G3["streamlit_uploader.py (Streamlit Ingest UI)"]
    end

    %% Flow connections
    A1 & A2 & A3 & A4 --> B1
    B1 --> B2 --> B3
    
    B3 -->|1. Resolve key| C1
    C1 -->|Query| C2
    C2 -->|Fetch approved map| C3
    C2 -->|No Map Found| C4
    C4 -->|Propose auto-learned mapping| C2
    
    C1 -->|2. Normalize unit| D1
    D1 -->|Fetch canonical unit & factor| D2
    
    D1 -->|3. Run checks| D3
    
    D3 -->|4. Log lineage| E1
    E1 -->|Insert audit record| E2
    
    E2 & C3 & D2 -->|Persist Metadata| F1
    B3 -->|Write normal value| F2
    
    F1 & F2 -->|Query Data| G1
    G1 -->|REST API feeds| G2 & G3
    G2 -->|Propose / Approve mappings| G1
```

---

## 3. Directory Layout

```text
├── cloud_metrics/
│   ├── api/
│   │   ├── metrics.py               # Legacy Ingestion Router
│   │   ├── query.py                 # Telemetry Query Endpoints
│   │   └── registry_api.py          # FASTAPI REST Registry Endpoints (New)
│   ├── classifiers/
│   │   └── ensemble_classifier.py   # Resolves keys via Mapping Registry before fallback matching
│   ├── ingestion/
│   │   ├── automated_mapper.py      # Core Ingestor (Source, Unit conversion, Rules, Provenance)
│   │   ├── aws.py                   # AWS CloudWatch connector
│   │   ├── gcp.py                   # GCP Monitoring connector
│   │   └── realtime_ingestor.py     # High-frequency ingestion endpoints
│   ├── models/
│   │   ├── asset.py                 # Asset Database Model
│   │   ├── cim_mapping.py           # Unified Mappings Database Model
│   │   ├── metric_definition.py     # Canonical Metric Definitions Model
│   │   ├── provenance.py            # Lineage Audit DB Model
│   │   ├── source.py                # Telemetry Source System Model
│   │   └── unit.py                  # QuantityKind & Unit DB Models
│   ├── registry/
│   │   └── namespace_registry.py    # Namespace verification
│   ├── services/
│   │   ├── mapping_registry_service.py     # Proposals, Approvals, and Resolvers
│   │   ├── provenance_registry_service.py  # Data Lineage logger
│   │   ├── rule_registry_service.py        # Constraint validation checks
│   │   └── unit_registry_service.py        # Unit conversions and normalizations
│   ├── scripts/
│   │   ├── admin_panel.py           # Streamlit Admin Portal dashboard
│   │   ├── seed_registries.py       # Seeds base metadata (Units, QK, Standards, Sources)
│   │   └── migrate_existing_data.py # Migrates legacy DB datacenters/keywords
│   └── main.py                      # Application startup & Router Mounting
├── migrations/                      # Alembic Database Migrations
└── tests/                           # Pytest Suite
```

---

## 4. Getting Started

### 4.1 Prerequisites
* **Python**: `3.13`
* **PostgreSQL**: Running instance (e.g. port `5433` for local development)
* **InfluxDB**: Used for time-series sample persistence

### 4.2 Configuration Setup
Copy `.env.sample` to `.env` in the root directory and configure environment connections:
```env
DATABASE_URL=postgresql+psycopg2://postgres:admin123@localhost:5433/cloud_metrics
INFLUXDB_URL=http://localhost:8086
INFLUXDB_TOKEN=my-token
INFLUXDB_ORG=my-org
INFLUXDB_BUCKET=cloud_metrics
```

### 4.3 Dependency Installation
To install core libraries and development dependencies:
```bash
poetry install
```

---

## 5. Database Schema Setup & Seed Data

### 5.1 Apply Schema Migrations
Database table generation is managed dynamically using Alembic:
```bash
# Upgrade the database schema to the latest head
poetry run alembic upgrade head
```

*Note: The migrations are fully compatible with downgrade paths:*
```bash
# To rollback to the initial schema
poetry run alembic downgrade -1
```

### 5.2 Database Seeding & Data Porting
Execute the seed script to load canonical units, quantity kinds (Energy, Power, DataSize), sources, and additional standards (SAREF, QUDT, PROV-O):
```bash
poetry run python cloud_metrics/scripts/seed_registries.py
```

Migrate legacy datacenter configurations and auto-learned mapping keywords into the new consolidated schemas:
```bash
poetry run python cloud_metrics/scripts/migrate_existing_data.py
```

---

## 6. Running the Application

### 6.1 FastAPI Backend REST Server
To launch the API server with hot-reload enabled:
```bash
poetry run uvicorn cloud_metrics.main:app --reload
```
Once started, the interactive OpenAPI documentation is available at [http://localhost:8000/docs](http://localhost:8000/docs).

### 6.2 Streamlit Admin Dashboard
To run the dashboard for editing mapping proposals, reviewing metadata, and browsing assets:
```bash
poetry run streamlit run cloud_metrics/scripts/admin_panel.py
```

---

## 7. Testing

The project utilizes `pytest` for unit and integration testing. Database connections are mocked using an isolated, transient SQLite database.

### 7.1 Running Tests
To run the full test suite (verifying units, API endpoints, mappings, rules, and telemetry pipelines):
```bash
poetry run pytest
```

### 7.2 Test Harness Isolation (SQLite Batch Mode)
During automated tests, standard database queries are mocked using SQLite:
```python
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    future=True
)
```
This is configured to bypass multi-threaded connection locks and ensure migrations execute correctly across different SQL dialects.

