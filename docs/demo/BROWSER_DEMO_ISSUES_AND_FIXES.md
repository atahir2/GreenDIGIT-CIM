# Milestone 16A — Issues and Fixes

Issues found while starting Postgres-backed apps and driving `sample_data/` through Chrome. Core orchestrator / mapping / KPI services were **not** redeshed. Only small validation-blocking defects were patched.

---

## Fixes applied (small, validation-blocking)

### F1 — Postgres boolean default on `cim_units.si_base` — **blocker** — fixed

- **Symptom**: `alembic upgrade head` failed: `column "si_base" is of type boolean but default expression is of type integer` (`BOOLEAN DEFAULT 0`).
- **Cause**: SQLite tests accept `0`; PostgreSQL does not.
- **Change**:
  - `migrations/versions/c2f8a1b9e047_add_cim_registry_tables.py`: `server_default=sa.text("false")`
  - `cloud_metrics/models/cim_registry.py`: `server_default="false"`
- **Why safe**: revision had never applied successfully on this Postgres database (transaction rolled back). Matches `docs/target/DATABASE_MIGRATION_PLAN.md` (`DEFAULT FALSE`).

### F2 — Postgres identifier length on lifecycle FK — **blocker** — fixed

- **Symptom**: `Identifier 'fk_cim_metric_lifecycle_links_lifecycle_stage_id_cim_lifecycle_stages' exceeds maximum length of 63 characters`.
- **Change**: renamed to `fk_cim_metric_lifecycle_links_stage_id` in the same migration and in `cim_registry.py`.
- **Tests**: `tests/test_cim_registry_migration.py` still pass (SQLite; no 63-char limit).

### F3 — `ingest_any._infer_domain` TypeError — **major** — fixed

- **Symptom**: browser warning `Generic loader failed ('tuple' object has no attribute 'lower')` for nested JSON/XML/YAML (`datacenter_A.json`, etc.).
- **Cause**: `_deep_items` yields `(path_tuple, value)`; code called `.lower()` on the tuple.
- **Change**: `cloud_metrics/utils/ingest_any.py` — collect last path segment and joined path as strings.
- **Result**: those files now parse with `Parser: ingest_any`.

### F4 — Influx hard-fail aborted uploader after Postgres writes — **major** — fixed

- **Symptom**: `Ingestion failed: ... WinError 10061` after metrics were already classified. Partner JSON export never ran.
- **Cause**: `write_mapped_metrics()` is required in the uploader; Influx was not running.
- **Change**: `cloud_metrics/scripts/streamlit_uploader.py` — catch Influx errors, `st.warning`, continue Postgres mapping + JSON export.
- **Not changed**: Influx client itself; operators should still run Influx for time-series.

### F5 — Windows `charmap` vs Streamlit emoji — **major** — fixed

- **Symptom**: after F4, `Ingestion failed: 'charmap' codec can't encode character '\u274c'`.
- **Cause**: redirected Windows stdout (cp1252) + `st.success("✅ …")` / `st.error("❌ …")`.
- **Change**: ASCII messages in the live uploader path.

### F6 — Unstructured `sample_data` TXT produced 0 metrics — **major** — fixed

- **Symptom**: `unstructured_dc_1.txt` / `_2.txt` → “No numeric metrics detected” because `ingest_any` only reads `key=value` lines and does not raise.
- **Change**: if `ingest_any` returns an empty metric map, the uploader falls back to the legacy parser (`legacy_core_empty_fallback`).
- **Result**: 6 and 2 metrics respectively.

### F7 — CSV/tempfile datacenter stem — **minor** — fixed

- **Symptom**: CSV datacenter labelled `tmpypi-03-mku` (NamedTemporaryFile stem).
- **Change**: if `meta.datacenter` matches the temp stem / `tmp*`, use the uploaded filename stem.

### F8 — Uploader result JSON — **minor** — fixed

- **Change**: success payload includes `unified_keys` so the browser shows mapped `gd.*` keys, not only a count.

---

## Follow-up (after MS16A): registry path wired into the workload UI

The user asked that remaining **legacy-path** limitations be resolved before Admin Portal validation.

### F9 — Streamlit uploader now uses the registry orchestrator — **major** — fixed

- `process_metric_sample(..., use_registry_orchestrator=True)` (same opt-in already used by `ingest_from_file`).
- Browser table shows `cim_namespace`, unit status, source/asset, lifecycle, standards, evidence, provenance id, extension id.
- Incompatible units are shown with `st.error` (not silent).
- CIM JSON / JSON-LD / provenance / crosswalk / evidence download buttons call existing `ExportService`.
- Partner `sample_data/` keys are aliased into the Mapping Registry via `ensure_workload_mappings()` (`origin=workload_sample`). Sample files were not changed.

Default `process_metric_sample(..., use_registry_orchestrator=False)` is unchanged for other callers.

### Still environmental / out of scope

- InfluxDB not running locally (time-series still optional after F4).
- `ifca.json` remains non-strict JSON (sample data not rewritten).
- Dedicated Scenario B/E files remain in `tests/fixtures/cim_demo/`, not `sample_data/`.

### O1 — Uploader does not enable the registry orchestrator — **major** — **resolved by F9**

The workload UI now passes `use_registry_orchestrator=True` and displays orchestrator metadata.

### O2 — InfluxDB not running — **major (environment)** — open

Time-series sink refused connections. After F4 this is a warning, not a hard UI failure. Docker Desktop was unavailable.

### O3 — Scenario B (wrong unit) not in `sample_data` — **minor (fixture gap)** — open

Dedicated file remains `tests/fixtures/cim_demo/wrong_units_sample.json`. The uploader now surfaces `unit_validation_status` when the orchestrator flags a unit.

### O4 — Scenario E extension candidates not created from uploads — **major** — **resolved by F9**

Unresolved keys now go through the orchestrator extension path; Candidate review should populate after a new upload.

### O5 — Partner `PUE` / `lambda.pue` not mapped to `cim:energy.efficiency.pue` — **major** — **resolved by F9**

`ensure_workload_mappings()` aliases partner keys (`PUE`, `lambda.pue`, `energy_wh`, …) onto the seeded CIM catalogue.

### O6 — `ifca.json` is not strict JSON — **minor** — open

JS-like keys (`SiteName: 'IFCA-LCG2'`). Generic JSON loader fails; legacy parser still extracts metrics. Sample data was not changed.

### O7 — Site ID often uses tempfile stem — **minor**

Even after F7, `site_id` can remain `tmp-….default_node.default_vm` while datacenter uses the real filename.

### O8 — Streamlit console 404 — **cosmetic**

One `Failed to load resource: 404` (favicon/static). Apps still rendered.

### O9 — `datetime.utcnow()` deprecation in uploader — **cosmetic**

Logged to stderr; not user-visible.

### O10 — No CIM export download on the uploader — **minor** — **resolved by F9**

Uploader now offers CIM JSON, JSON-LD (partial), provenance, standards crosswalk, and evidence readiness downloads via `ExportService`.

JSON-LD / RO-Crate-style / DCAT-style remain API/CLI (`/api/v1/cim-export/`). Partner `gd.*` JSON path is shown after ingest.

---

## Classification summary

| ID | Severity | Status |
|----|----------|--------|
| F1 boolean default | blocker | fixed |
| F2 FK name length | blocker | fixed |
| F3 ingest_any domain infer | major | fixed |
| F4 Influx hard-fail | major | fixed |
| F5 Windows emoji encoding | major | fixed |
| F6 unstructured empty fallback | major | fixed |
| F7 tempfile datacenter | minor | fixed |
| F8 unified_keys in UI JSON | minor | fixed |
| F9 uploader uses registry orchestrator | major | fixed |
| O1 no orchestrator on uploader | major | resolved by F9 |
| O2 Influx down | major env | open |
| O3 no wrong-unit sample_data file | minor | open |
| O4 no extension candidates | major | resolved by F9 |
| O5 PUE not CIM-mapped from partner keys | major | resolved by F9 |
| O6 ifca.json syntax | minor | open |
| O7 tempfile site_id | minor | mitigated |
| O8 404 console | cosmetic | open |
| O9 utcnow | cosmetic | open |
| O10 no semantic export on uploader | minor | resolved by F9 |
