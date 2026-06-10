# Current CIM Architecture — GreenDIGIT

> **Generated**: 2026-06-10 · **Scope**: Full architecture audit (read-only)

---

## 1. System Overview

The GreenDIGIT CIM (Common Information Model) system is a **metric ingestion, classification, and normalization pipeline** for data center sustainability metrics. It takes heterogeneous metric data from multiple partners (cloud, grid, network providers) in varied formats and maps them into a unified namespace (`gd.category.subcategory.short_key`).

### High-Level Architecture

```mermaid
graph TB
    subgraph "Data Sources"
        F["File Upload<br/>(JSON/YAML/XML/CSV/TXT)"]
        API["Cloud APIs<br/>(AWS/GCP stubs)"]
        RT["Realtime API<br/>(dict payloads)"]
    end

    subgraph "Ingestion Layer"
        SU["Streamlit Uploader UI"]
        FI["FastAPI /metrics/*"]
        UIF["unified_ingestion.py"]
        RTE["realtime_ingestor.py"]
    end

    subgraph "Parsing Layer"
        IA["ingest_any.py<br/>(universal loader)"]
        SP["structured_parser.py"]
        UP["unstructured_parser.py"]
        PP["partner_payload.py"]
        MD["metadata.py"]
    end

    subgraph "Classification Layer"
        AM["automated_mapper.py<br/>(orchestrator)"]
        SC["semantic_classifier.py"]
        AC["alias_classifier.py"]
        EC["ensemble_classifier.py"]
        FB["fallbacks.py"]
        KL["keyword_learning.py"]
    end

    subgraph "Namespace & Registry"
        NR["namespace_registry.py"]
        MR["mapping_registry.py"]
        NG["namespace_generator.py"]
        SR["standards_registry.py"]
        UK["unified_key.py"]
        MS["mapping_sync.py"]
    end

    subgraph "Storage Layer"
        PG[("PostgreSQL<br/>11 tables")]
        IX[("InfluxDB 2.x<br/>time-series")]
        MJ["metric_mapping.json<br/>(file-based cache)"]
        EJ["Exported JSON<br/>(partner output)"]
    end

    F --> SU --> IA --> AM
    F --> UIF --> SP --> AM
    F --> UIF --> UP --> AM
    API --> FI --> AM
    RT --> RTE --> AM

    AM --> SC
    AM --> AC
    AM --> EC
    EC --> FB

    AM --> NR
    AM --> MR
    AM --> KL
    AM --> SR

    NR --> PG
    MR --> PG
    MR --> MS --> MJ
    AM --> PG
    AM --> IX
    AM --> EJ
```

---

## 2. Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **API** | FastAPI + Uvicorn | REST endpoints for ingestion & query |
| **UI** | Streamlit (2 apps) | File upload portal + Admin review panel |
| **ORM** | SQLAlchemy 2.0 | PostgreSQL access (11 tables) |
| **Config** | pydantic-settings + python-dotenv | Environment-based configuration |
| **Time-Series** | InfluxDB 2.x (influxdb-client) | Metric value storage + Flux queries |
| **RDBMS** | PostgreSQL 15 | Metadata, taxonomy, mappings, audit trail |
| **Classification** | RapidFuzz + sentence-transformers | Fuzzy matching + embedding similarity |
| **Parsing** | json, PyYAML, xml.etree, csv | Multi-format file parsing |
| **CI** | GitHub Actions | Automated testing pipeline |
| **Containerization** | Docker Compose | PostgreSQL + InfluxDB services |

---

## 3. Core Architectural Patterns

### 3.1 Dual Storage Architecture

The system uses **two complementary databases**:

1. **PostgreSQL** (via SQLAlchemy) — stores:
   - Taxonomy hierarchy (standards → categories → subcategories)
   - Metric definitions (unified keys, sources, tags)
   - Metric samples (per-observation records with classification metadata)
   - Mapping audit trail (proposals, events, source maps)
   - Datacenter registry + upload logs
   - Keyword learning cache

2. **InfluxDB** — stores:
   - Time-series metric values (measurement=unified_key, value=float, tags, timestamp)
   - Used for range queries and analytics

3. **JSON file** (`metric_mapping.json`) — acts as:
   - Fast-path cache for raw→unified lookups
   - Synchronization artifact between DB state and runtime

### 3.2 Classification Pipeline (Ensemble)

The system employs a **cascading classifier** in `ensemble_classifier.py`:

```
Priority Chain:
  1. semantic_classifier   → Exact suffix match against 10 known patterns (conf=0.90)
  2. alias_classifier      → Fuzzy match (RapidFuzz WRatio ≥ 88) against ~80 aliases (conf=0.85+)
  3. rule_guess            → Token intersection rules (conf=0.60–0.80)
  4. embed_guess           → Sentence-transformer cosine similarity ≥ 0.60 (optional)
  5. fallback              → Returns ("uncategorized", "unknown", "unknown", 0.0)
```

**Problem**: `automated_mapper.py` contains a **parallel, independent `_classify_to_parts()`** function (L55–130) that duplicates the ensemble pipeline with its own rules, effectively creating two competing classification paths.

### 3.3 Namespace Convention

All unified metric keys follow the pattern:
```
gd.<category>.<subcategory>.<short_key>
```

Examples:
- `gd.energy.consumption.total`
- `gd.performance.cpu.utilization`
- `gd.environment.temperature.interior`
- `gd.network.traffic.incoming`

The `to_gd()` utility normalizes any key format into this 4-part structure.

### 3.4 Auto-Learning

When classification confidence ≥ 0.85:
- The raw_key → (category, subcategory, short_key) mapping is stored in `metric_keywords`
- Next occurrence is resolved via DB lookup (O(1)) before fuzzy matching

### 3.5 Standards Linkage

After classification, unified keys are matched to sustainability standards via rule-based inference:
- `gd.energy.efficiency.pue` → TGG-PUE (conf=0.99)
- `gd.environment.emissions.*` → GHG (conf=0.85)
- `gd.energy.*` → ISO-50001 (conf=0.60, umbrella)
- `gd.environment.temperature.*` → ASHRAE-TC9.9-2021 (conf=0.80)

---

## 4. Module Dependency Graph

```mermaid
graph LR
    subgraph "Entry Points"
        main["main.py<br/>(FastAPI)"]
        stup["streamlit_uploader.py"]
        adm["admin_panel.py"]
    end

    subgraph "Core Pipeline"
        am["automated_mapper.py"]
        ec["ensemble_classifier.py"]
        ac["alias_classifier.py"]
        sc["semantic_classifier.py"]
        fb["fallbacks.py"]
    end

    subgraph "Data Access"
        cfg["config.py"]
        ifl["influx_service.py"]
        idc["insert_datacenter.py"]
        imd["insert_mapped_metric.py"]
        ims["insert_metric_sample.py"]
        kl["keyword_learning.py"]
        sr["standards_registry.py"]
    end

    subgraph "Registry"
        nr["namespace_registry.py"]
        mr["mapping_registry.py"]
        msync["mapping_sync.py"]
    end

    main --> am
    stup --> am
    adm --> ec

    am --> ec --> ac
    am --> sc
    ec --> sc
    ec --> fb
    am --> nr
    am --> mr
    am --> kl
    am --> imd
    am --> ims
    am --> idc
    am --> msync

    imd --> sr
    imd --> msync
    mr --> imd
    mr --> msync

    cfg --> ifl
    cfg --> idc
    cfg --> imd
    cfg --> ims
```

---

## 5. Database Schema (PostgreSQL — 11 Tables)

```mermaid
erDiagram
    standards {
        int id PK
        text code UK
        text name
        text url
        text description
    }

    categories {
        int id PK
        string name UK
        int standard_id FK
        text description
    }

    subcategories {
        int id PK
        string name
        int category_id FK
        text description
    }

    metric_definitions {
        int id PK
        string unified_key UK
        json tags
        json sources
        datetime created_at
    }

    metric_samples {
        int id PK
        int datacenter_id FK
        string unified_key
        string raw_key
        float value
        string unit
        json tags
        string source_file
        datetime captured_at
        string ri_id
        string node_id
        string vm_id
        string host
        string site_id
        float clf_confidence
        text clf_rationale
        text domain
        jsonb extra_meta
    }

    metric_keywords {
        int id PK
        string keyword UK
        string category
        string subcategory
        string short_key
        string source_key
        datetime created_at
    }

    metric_mappings {
        int id PK
        string raw_key UK
        string unified_key
        int version
        string unit
        json tags
        datetime approved_at
    }

    mapping_proposals {
        int id PK
        string raw_key
        string suggested_unified_key
        float confidence
        string rationale
        string unit
        json tags
        enum status
        datetime created_at
    }

    mapping_events {
        int id PK
        string raw_key
        string event
        json payload
        datetime created_at
    }

    metric_source_map {
        int id PK
        int datacenter_id FK
        string raw_key
        string unified_key
        datetime first_seen
        datetime last_seen
    }

    datacenters {
        int id PK
        string name UK
        string location
        string provider
        datetime created_at
    }

    file_upload_logs {
        int id PK
        string filename
        int datacenter_id FK
        string uploaded_by
        datetime uploaded_at
    }

    metric_standard_map {
        int id PK
        int metric_definition_id FK
        int standard_id FK
        text standard_metric_code
        float confidence
        text rationale
    }

    standards ||--o{ categories : "has"
    categories ||--o{ subcategories : "has"
    metric_definitions ||--o{ metric_standard_map : "linked via"
    standards ||--o{ metric_standard_map : "linked via"
    datacenters ||--o{ metric_samples : "has"
    datacenters ||--o{ file_upload_logs : "has"
    datacenters ||--o{ metric_source_map : "has"
```

---

## 6. Existing Strengths

| Strength | Evidence |
|----------|----------|
| **Multi-format support** | Handles JSON, YAML, XML, CSV, TXT, NDJSON, partner payloads — graceful fallbacks |
| **Cascading classification** | 5-level ensemble: semantic → alias → rules → embeddings → fallback |
| **Self-learning** | High-confidence classifications auto-persist to `metric_keywords` for O(1) future lookups |
| **Standards linkage** | Automated rule-based mapping to 12 sustainability standards (TGG, GHG, ISO, ASHRAE, IEEE, etc.) |
| **Atomic JSON sync** | `mapping_sync.py` uses temp-file + os.replace for crash-safe writes |
| **Admin review workflow** | Streamlit admin panel allows human review of uncategorized metrics with retrofix capability |
| **Flexible metadata extraction** | Deep-scan strategy handles arbitrary JSON nesting; partner-generic strategy handles cloud/grid/network payloads |
| **Audit trail** | `MappingEvent` table provides append-only history; `MappingProposal` supports proposal/approval workflow |
| **Dual storage** | PostgreSQL for metadata + InfluxDB for time-series — appropriate separation of concerns |
| **gd.* namespace convention** | Consistent 4-part unified key format across all outputs |
