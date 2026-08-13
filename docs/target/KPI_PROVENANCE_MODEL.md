# KPI Provenance Model

> **Milestone 13**

Every `KpiCalculationService` call that has a DB session writes a `cim_provenance_records` row, including **blocked** and **invalid_unit** outcomes.

| Field | Value |
|-------|--------|
| `entity_type` | `kpi_calculation` |
| `entity_id` | KPI metric definition id when known |
| `activity` | `kpi_calculation` |
| `agent` | `kpi_calculation_service` |
| `method` | `KpiCalculationService` |
| `inputs` | namespace, raw values, normalized values/units, period, boundary, source |
| `outputs` | value, unit, `calculation_status`, `reportable_approved`, errors |
| `notes` | formula string |

Result exposes `provenance_record_id`.

This is additive to orchestrator provenance (`orchestration`, `unit_validation`, …). Review actions remain `review_action` (Milestone 12).
