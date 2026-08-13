# Milestone 16A — Browser Demo Screenshot Index

Screenshots: `docs/demo/screenshots/ms16a/`. Captured from Google Chrome (Playwright `channel="chrome"`, headed, 1400×900) on 2026-08-13.

| File | What it shows |
|------|----------------|
| `00_api_health.png` | `GET http://127.0.0.1:8000/health` → `{"status":"ok"}` |
| `01_api_docs.png` | FastAPI Swagger: ingest, registry, cim-review, cim-kpi, cim-export |
| `02_uploader_landing.png` | User-facing page: **Ingestion Uploader (Any Format)**, file picker, “Choose a file to start.” |
| `uploader_datacenter_a_json.png` | Scenario A+D. 15 parsed / 14 written. `gd.*` unified_keys including unknown `lambda.pue`/`lambda.wue`. Influx skip warning. Ingestion complete. Partner JSON export path. |
| `uploader_datacenter_b_xml.png` | Scenario A. XML accepted, ingest_any, 10 metrics, complete. |
| `uploader_datacenter_c_csv.png` | Scenario A. CSV, 4 metrics, datacenter_C, complete. |
| `uploader_datacenter_d_yaml.png` | Scenario A. YAML, 4 metrics, complete. |
| `uploader_datacenter_z_json.png` | Partial operational JSON. 4 metrics. Datacenter `unknown`. |
| `uploader_payload_cloud_json.png` | Scenario C+D. domain=`cloud`, 12 metrics, exec unit in site_id, complete. |
| `uploader_payload_grid_json.png` | Scenario C+D. domain=`grid`, 15 metrics, complete. |
| `uploader_payload_network_json.png` | Scenario C + network. domain=`network`, 8 metrics, complete. |
| `uploader_ifca_json.png` | Scenario C. Invalid strict JSON → legacy parser, 8 metrics, complete. |
| `uploader_unstructured_dc_1_txt.png` | Unstructured text. ingest_any empty → legacy fallback, 6 metrics. |
| `uploader_unstructured_dc_2_txt.png` | Unstructured text. legacy fallback, 2 metrics, complete. |
| `90_admin_landing.png` | Admin portal after uploads (unknown-metrics default section). |
| `91_admin_unknown_metrics_legacy.png` | Legacy unknown-key queue populated from workload files (`lambda.pue`, `lambda.wue`, `doc0.ExecUnitFinished`, …). |
| `91_admin_unknown_metrics_legacy_error.png` | First-pass capture of the same section (sidebar radio click timed out; page content still valid). |
| `91_admin_registry_browser.png` | 20 seeded CIM metric definitions (`cim:…`). |
| `91_admin_candidate_review.png` | Empty CIM candidate queue after workload uploads. |
| `91_admin_evidence_readiness.png` | PUE/WUE/CUE/workflow evidence catalogues; ISO-IEC-30134 mandatory; missing fulfillment. |
| `91_admin_kpi_calculation.png` | PUE calculator form (monthly / facility / 1200 / 800 kWh). |
| `91_admin_provenance_timeline.png` | Only seed bootstrap provenance (no upload orchestration). |

Full-page PNG filenames for uploads follow `uploader_<file_stem>.png`.
