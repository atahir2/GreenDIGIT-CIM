# Milestone 16A — Browser Demo Run Log

> **Run window**: 2026-08-13 13:13–13:15 UTC (final successful Chrome pass)  
> **Machine**: Windows 10, Google Chrome, project `.venv` Python 3.13.2  
> **Raw JSON**: `docs/demo/logs/ms16a/browser_run_results.json`  
> **Process logs**: `docs/demo/logs/ms16a/fastapi.*.log`, `uploader.*.log`, `admin.*.log`

---

## 1. Startup sequence

1. Confirmed `.env` `DATABASE_URL` → Postgres `localhost:5433/cloud_metrics`.
2. `alembic current` was `a7708d6bee50` (pre-CIM tables). First `alembic upgrade head` failed (boolean default + FK name). After the two migration fixes, upgrade reached `c2f8a1b9e047`.
3. `python -m cloud_metrics.scripts.seed_cim_registries --json` created catalogues (20 metrics, 23 units, …).
4. `python -m cloud_metrics.scripts.seed_registries` (legacy units/sources; `file_upload` already present).
5. Started:
   - uvicorn `cloud_metrics.main:app` on `127.0.0.1:8000`
   - Streamlit uploader on `127.0.0.1:8501`
   - Streamlit admin on `127.0.0.1:8502`
6. Health: `GET /health` → `{"status":"ok"}`; both Streamlit apps HTTP 200.
7. Influx `:8086` closed. Docker Desktop engine not running.
8. Opened Google Chrome via Playwright `channel="chrome"` (headed). Playwright is **not** in `requirements.txt`; installed only in this session.

---

## 2. URLs tested

| URL | Purpose |
|-----|---------|
| http://127.0.0.1:8000/health | API health |
| http://127.0.0.1:8000/docs | OpenAPI: registry, review, KPI, export |
| http://127.0.0.1:8000/api/v1/cim-export/json | Export JSON (HTTP 200) |
| http://127.0.0.1:8000/api/v1/cim-export/evidence-readiness | Evidence export (HTTP 200) |
| http://127.0.0.1:8501 | Workload uploader |
| http://127.0.0.1:8502 | Admin portal sections |

---

## 3. Chrome upload pass (final)

All files from `sample_data/`. Influx write skipped with a warning; Postgres + `gd.*` mapping + partner JSON continued.

| File | Scenario tag | Parser | Found | Ingestion complete | Notes |
|------|--------------|--------|-------|--------------------|-------|
| datacenter_A.json | A+D | ingest_any | 15 | Yes | 14 unified keys written; pue/wue as `gd.custom.unknown.*`; export `cloud_metrics\data\exports\datacenter_A_unified.json` |
| datacenter_B.xml | A | ingest_any | 10 | Yes | |
| datacenter_C.csv | A | ingest_any | 4 | Yes | Datacenter label corrected from tempfile stem |
| datacenter_D.yaml | A | ingest_any | 4 | Yes | |
| datacenter_Z.json | A partial | ingest_any | 4 | Yes | Datacenter shown as `unknown`; site_id `node01` |
| payload_cloud.json | C+D | ingest_any | 12 | Yes | domain=`cloud`, site `eu-central-1-cloud-site.exec-cloud-001` |
| payload_grid.json | C+D | ingest_any | 15 | Yes | domain=`grid` |
| payload_network.json | C+network | ingest_any | 8 | Yes | domain=`network` |
| ifca.json | C | legacy_core | 8 | Yes | Not strict JSON (`SiteName:`). Generic loader failed; legacy fallback |
| unstructured_dc_1.txt | A unstructured | legacy_core_empty_fallback | 6 | Yes | ingest_any found 0 (key=value only); legacy regex extracted 6 |
| unstructured_dc_2.txt | A unstructured | legacy_core_empty_fallback | 2 | Yes | |

**11/11** files: accepted + Ingest clicked + `Ingestion complete`.

Earlier passes (same day) failed for documented reasons and were re-run after small fixes:

1. Influx connection refused aborted the UI after metrics were already classified.
2. `ingest_any._infer_domain` `'tuple' object has no attribute 'lower'` forced legacy parse on nested JSON/XML/YAML.
3. Windows `charmap` could not encode `✅`/`❌` in Streamlit success/error once ingest reached `st.success`.

---

## 4. Example mapped keys (browser JSON)

From `datacenter_A.json` uploader result (`unified_keys`):

```text
gd.performance.cpu.utilization
gd.performance.memory.usage
gd.energy.consumption.total
gd.custom.unknown.alphaenergyrenewable
gd.custom.unknown.alphanetin
gd.custom.unknown.alphanetout
gd.storage.disk.read_io
gd.storage.disk.write_io
gd.environment.temperature.ambient
gd.custom.unknown.lambdapue
gd.custom.unknown.lambdawue
gd.custom.unknown.lambdacfp
gd.energy.power.total
gd.custom.unknown.lambdawush
```

From partner payloads, `PUE` → `gd.custom.unknown.unknown`; `energy_wh` → `gd.energy.consumption.total`; boolean-like `job_finished` / `execunitfinished` → `gd.custom.unknown.*`.

---

## 5. Admin portal inspection (same Chrome session)

| Section | Observed |
|---------|----------|
| Unknown metrics (legacy) | Unknown raw keys from the uploads (e.g. `lambda.pue`, `lambda.wue`, `doc0.ExecUnitFinished`) |
| Registry browser | 20/20 seeded CIM metrics (`cim:energy.power.total`, facility PUE inputs, workflow energy, …) |
| Candidate review | “No candidate / under_review entries.” |
| Evidence readiness | PUE/WUE/CUE/workflow energy declared; PUE ISO-IEC-30134 mandatory rows; missing fulfillment |
| KPI calculation | Form ready: PUE, monthly, facility, 1200 / 800 kWh (Calculate not clicked — MS16B) |
| Provenance timeline | Single row: seed `bootstrap` / `milestone3_seed`. No upload orchestration records |

---

## 6. Backend log excerpts (uploader)

Unit warnings (not shown in the browser):

```text
Validation warning: metric 'gd.performance.cpu.utilization' is numeric but has no unit specified
Unit conflict: energy metric 'gd.energy.consumption.total' has invalid unit 'kwh' (expected Energy quantity unit like kWh)
```

Influx (shown in the browser as a warning after the soft-fail fix):

```text
Influx time-series write skipped (sink unavailable): ... [WinError 10061] ...
```

---

## 7. Browser console

One console error across the session:

```text
Failed to load resource: the server responded with a status of 404 (Not Found)
```

No application `pageerror`. Treated as Streamlit static/favicon noise (cosmetic).

---

## 8. Database after the run

- `metric_samples`: 850 rows (includes prior local data plus this session).
- Recent origins include `datacenter_A`, `eu-central-1-cloud-site`, `ifca`, `unstructured_dc_1`, `unstructured_dc_2`.
- `cim_provenance_records`: 1 (registry seed only).
- `cim_extension_metrics`: 0.
- `cim_metric_mappings`: 21 (seeded, not demo `origin=demo` rows).
