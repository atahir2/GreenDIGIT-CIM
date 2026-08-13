# Milestone 13 — KPI Calculation Service

Explicit PUE / WUE / CUE calculation with reportable hard-block policy and provenance. No generic formula engine. Ingestion and orchestrator unchanged.

## Deliverables

| Artifact | Path |
|----------|------|
| Service | `cloud_metrics/registry/kpi/` |
| CLI | `cloud_metrics/scripts/calculate_kpi.py` |
| API | `POST /api/v1/cim-kpi/{pue\|wue\|cue}` |
| Tests | `tests/test_kpi_calculation_service.py` |
| Docs | `docs/target/KPI_*.md`, `LEGACY_KPI_CALCULATION_HANDLING.md` |

## Next

Admin UI for review queues; optional wiring of calculated KPIs into the Milestone 10 facility demo; evidence fulfillment tracking.
