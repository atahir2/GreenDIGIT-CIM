# Milestone 16A — Browser End-to-End CIM Workload Validation

> **Date**: 2026-08-13  
> **Scope**: User-facing demo/workload flow in the browser using `sample_data/`  
> **Status**: Completed (validation). Orchestrator field coverage in the uploader is **partial**.

This milestone does **not** add CIM architecture. It starts the local apps, opens Google Chrome, uploads each `sample_data` file through the Streamlit ingestion UI, and records what the browser actually shows versus the Scenario A–E expectations from Milestone 10.

---

## 1. How to run the CIM application locally

Poetry is not required. This machine uses the project virtualenv.

| Item | Command / value |
|------|-----------------|
| Python | `.venv\Scripts\python.exe` (3.13.2) |
| Backend / API | `.venv\Scripts\python.exe -m uvicorn cloud_metrics.main:app --host 127.0.0.1 --port 8000` |
| User-facing upload UI | `.venv\Scripts\python.exe -m streamlit run cloud_metrics/scripts/streamlit_uploader.py --server.port 8501 --server.address 127.0.0.1 --server.headless true` |
| Admin portal (result inspection) | `.venv\Scripts\python.exe -m streamlit run cloud_metrics/scripts/admin_panel.py --server.port 8502 --server.address 127.0.0.1 --server.headless true` |
| Schema | `.venv\Scripts\python.exe -m alembic upgrade head` |
| CIM seed | `.venv\Scripts\python.exe -m cloud_metrics.scripts.seed_cim_registries` |
| Legacy unit/source seed | `.venv\Scripts\python.exe -m cloud_metrics.scripts.seed_registries` |
| Sample files | `sample_data/` (repository root) |
| Env file | `.env` (gitignored). Required: `DATABASE_URL`. Influx vars are optional for Postgres ingest. |

Required environment variables (from `.env`):

```text
DATABASE_URL=postgresql+psycopg2://postgres:admin123@localhost:5433/cloud_metrics
INFLUX_URL=...          # optional; unused if Influx is down
INFLUX_TOKEN=...
INFLUX_ORG=...
INFLUX_BUCKET=...
CORS_ORIGINS=http://localhost:3000,http://localhost:8000
METRIC_MAPPING_JSON_PATH=cloud_metrics/data/metric_mapping.json
```

This validation used PostgreSQL 17 on `localhost:5433`. InfluxDB was **not** running on `:8086`. Docker Desktop was not running.

Reproducible Chrome runner (session Playwright package, uses installed Google Chrome; not a project dependency):

```text
.venv\Scripts\python.exe -m pip install playwright
.venv\Scripts\python.exe docs/demo/ms16a_browser_runner.py
```

---

## 2. App startup verification

| URL | Result |
|-----|--------|
| http://127.0.0.1:8000/health | `{"status":"ok"}` |
| http://127.0.0.1:8000/docs | FastAPI Swagger UI (ingest, registry, review, KPI, export) |
| http://127.0.0.1:8501 | Streamlit **Ingestion Uploader (Any Format)** |
| http://127.0.0.1:8502 | Streamlit **CIM Admin Portal** |

Alembic head after this run: `c2f8a1b9e047`. CIM seed created 20 metrics, 23 units, 10 lifecycle stages, 15 standards, 8 rules, 6 evidence requirements.

---

## 3. User-facing demo / workload page

The browser workload page is **not** the admin portal and **not** `/docs`.

| Role | URL |
|------|-----|
| Workload upload / ingest | http://127.0.0.1:8501 |
| Registry / review / KPI / provenance inspection | http://127.0.0.1:8502 |
| REST / export | http://127.0.0.1:8000/docs |

There is no FastAPI file-upload ingest endpoint. AWS/GCP ingest routes are GET triggers only.

The uploader calls `process_metric_sample()` **without** `use_registry_orchestrator=True`. Unified file ingestion (`ingest_from_file`) enables the orchestrator; the Streamlit uploader does not. That is why the browser workload flow emits `gd.*` keys and does not create per-sample CIM provenance / extension candidates.

---

## 4. `sample_data` files vs Scenario A–E

Dedicated Milestone 10 fixtures live under `tests/fixtures/cim_demo/` (`known_metrics_sample.json`, `wrong_units_sample.json`, `workflow_run_metrics_sample.json`, `facility_kpi_sample.json`, `unknown_metrics_sample.json`). Those files were **not** modified and were **not** copied into `sample_data/`.

| `sample_data` file | Closest scenario | Parser used | Metrics found | Browser ingest |
|--------------------|------------------|-------------|----------------|----------------|
| `datacenter_A.json` | A + D (cpu/mem/energy + pue/wue) | `ingest_any` | 15 | Pass (14 written) |
| `datacenter_B.xml` | A | `ingest_any` | 10 | Pass |
| `datacenter_C.csv` | A | `ingest_any` | 4 | Pass |
| `datacenter_D.yaml` | A | `ingest_any` | 4 | Pass |
| `datacenter_Z.json` | A (partial metadata+metrics mix) | `ingest_any` | 4 | Pass |
| `payload_cloud.json` | C + D (job context, PUE, energy) | `ingest_any` | 12 | Pass |
| `payload_grid.json` | C + D | `ingest_any` | 15 | Pass |
| `payload_network.json` | C + network | `ingest_any` | 8 | Pass |
| `ifca.json` | C (job energy/work; JS-like JSON) | `legacy_core` | 8 | Pass |
| `unstructured_dc_1.txt` | A unstructured | `legacy_core_empty_fallback` | 6 | Pass |
| `unstructured_dc_2.txt` | A unstructured | `legacy_core_empty_fallback` | 2 | Pass |

**Not present in `sample_data/`:** a dedicated wrong-unit file (Scenario B) and a dedicated unknown/custom CIM demo file (Scenario E). Unknown keys still appeared as a side-effect of partner files (`lambda.pue`, `PUE`, `execunitfinished`, …).

---

## 5. What the browser shows per upload

On http://127.0.0.1:8501 after **Ingest**, the UI shows:

| Expected field | Visible in uploader? |
|----------------|----------------------|
| Input file accepted | Yes (filename + size) |
| Parsed metric count | Yes (`Found N metrics`) |
| Mapped unified keys | Yes (`unified_keys` JSON, `gd.*`) |
| Partner JSON export path | Yes (when export runs) |
| Resolved **CIM** namespace (`cim:*`) | **No** (legacy `gd.*` path) |
| Unit validation status | **No** (warnings only in uploader process log) |
| Source resolution status | **No** |
| Asset resolution status | **No** |
| Lifecycle stages | **No** (seeded catalogue visible in admin Registry/Evidence only) |
| Standards mappings | **No** (seeded catalogue visible in admin Evidence) |
| Governance validation | **No** |
| Evidence requirements | **No** on uploader; **Yes** on admin Evidence readiness (catalogues, not this sample) |
| Provenance record for the upload | **No** (admin Provenance shows seed bootstrap only) |
| Extension candidate | **No** (admin Candidate review empty; legacy Unknown metrics page lists `gd.custom.unknown.*`) |
| CIM export/download (JSON-LD / RO-Crate / DCAT) | **No** on uploader; **Yes** as API under `/api/v1/cim-export/` |

---

## 6. Scenario outcomes

### Scenario A — known operational metric — **PARTIAL PASS**

Partner files map operational keys such as CPU, memory, energy, power, network, and disk to `gd.*` namespaces (example from `datacenter_A.json`: `gd.performance.cpu.utilization`, `gd.energy.consumption.total`, `gd.energy.power.total`). Files are accepted; ingest completes; no crash after the small UI/parser fixes.

Not met in the workload UI: mapping to approved `cim:compute.node.power.draw` (and siblings), visible unit validity, source/asset resolution, lifecycle/standards, orchestrator provenance.

### Scenario B — wrong unit — **NOT EXERCISABLE FROM `sample_data` / FAIL for UI flag**

No dedicated incompatible-unit file exists in `sample_data/`. Backend logs for `datacenter_A.json` / `datacenter_Z.json` recorded `Unit conflict: ... invalid unit 'kwh'` (symbol case). The browser does **not** display that conflict; ingest is still reported complete. Incompatible units are not visibly flagged in the workload UI.

### Scenario C — workflow / reproducibility — **PARTIAL PASS**

`payload_cloud.json`, `payload_grid.json`, `payload_network.json`, and `ifca.json` preserve job/run context in parser metadata (`domain=cloud|grid|network`, `site_id` includes `exec-*`). Energy maps to `gd.energy.consumption.total`. Workflow keys are **not** mapped to `cim:workflow.*`. PROV-O / RO-Crate / schema.org packages are not shown in the uploader; FastAPI exposes partial export endpoints. No ISO/EN `exactMatch` is asserted in the uploader (nothing is shown).

### Scenario D — facility / KPI — **PARTIAL PASS (admin catalogue, not sample mapping)**

`lambda.pue` / payload `PUE` land as `gd.custom.unknown.*`, not `cim:energy.efficiency.pue`. Admin **Evidence readiness** shows seeded PUE/WUE/CUE mandatory ISO/IEC 30134 evidence and missing fulfillment. Admin **KPI calculation** shows PUE inputs (1200/800 kWh, monthly, facility) ready to calculate. The workload upload does not compute PUE or show missing boundary/period for the uploaded file.

### Scenario E — unknown / custom — **PARTIAL PASS (legacy unknown queue, not Extension Registry)**

Unknown keys become `gd.custom.unknown.*` and appear on admin **Unknown metrics (legacy)**. They are not auto-approved CIM namespaces. Admin **Candidate review** showed *No candidate / under_review entries* because the uploader never created `cim_extension_metrics` rows. No per-sample provenance.

---

## 7. Tests

| Suite | Result |
|-------|--------|
| `pytest tests/test_cim_registry_migration.py tests/test_cim_end_to_end_demo.py -q` | **22 passed** |
| Browser uploads (`sample_data`, 11 files) | **11/11 Ingestion complete** after small fixes |
| `GET /api/v1/cim-export/json` | 200 |
| `GET /api/v1/cim-export/evidence-readiness` | 200 |

Milestone 10 CLI scenarios A–E remain the authoritative orchestrator checks (`python -m cloud_metrics.scripts.run_cim_demo`). They were not re-run as a substitute for browser workload validation.

---

## 8. Recommendation

**Proceed to Admin Portal browser validation (MS16B).** The admin portal is already the only browser surface that shows CIM registries, evidence, KPI calculation, and provenance. MS16A showed that the user-facing uploader is a working partner-file ingest path (`gd.*`) and is **not** the registry-orchestrator demonstrator.

A separate product decision (not made here): whether Streamlit upload should pass `use_registry_orchestrator=True` like `ingest_from_file`. That would be required before Scenario A–E orchestrator fields can appear from workload files in the browser.

See also: [BROWSER_DEMO_RUN_LOG.md](BROWSER_DEMO_RUN_LOG.md), [BROWSER_DEMO_SCREENSHOT_INDEX.md](BROWSER_DEMO_SCREENSHOT_INDEX.md), [BROWSER_DEMO_ISSUES_AND_FIXES.md](BROWSER_DEMO_ISSUES_AND_FIXES.md).
