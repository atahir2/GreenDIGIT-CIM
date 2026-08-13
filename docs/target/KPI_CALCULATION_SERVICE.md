# KPI Calculation Service

> **Milestone 13** · Explicit PUE / WUE / CUE calculation with hard-block validation and provenance

## Purpose

`KpiCalculationService` (`cloud_metrics/registry/kpi/`) computes reportable sustainability KPIs from validated inputs. It is **not** a generic formula engine and does **not** change orchestrator or ingestion behaviour.

Aliases: `CimKpiCalculationService`, `SustainabilityKpiService`.  
Factory: `get_kpi_calculation_service(session)`.

## Methods

| Method | Formula | Result unit |
|--------|---------|-------------|
| `calculate_pue(facility_energy, it_energy, …)` | facility energy / IT energy | `ratio` (dimensionless) |
| `calculate_wue(water_usage, it_energy, …)` | water volume / IT energy | `L/kWh` |
| `calculate_cue(carbon, it_energy, …)` | carbon mass / IT energy | `kgCO2e/kWh` |
| `calculate("pue"\|"wue"\|"cue", **inputs)` | dispatcher | as above |

## Result (`KpiCalculationResult`)

`kpi_namespace`, `value`, `unit`, `input_metrics`, `input_values`, `normalized_inputs`, `aggregation_period`, `boundary`, `validation_status`, `evidence_requirements`, `standards_mappings`, `provenance_record_id`, `warnings`, `errors`, `calculation_status`, `reportable_approved`.

`calculation_status`: `calculated` | `blocked` | `missing_input` | `invalid_unit` | `under_review`.

## Callers

- CLI: `python -m cloud_metrics.scripts.calculate_kpi pue --facility 1200 --it 800 --period monthly --boundary facility`
- API: `POST /api/v1/cim-kpi/{pue|wue|cue}`
- Tests / services: construct `KpiInput` or dicts

Ingestion and `RegistryOrchestratorService` are unchanged. Operational samples still use soft unit warnings.
