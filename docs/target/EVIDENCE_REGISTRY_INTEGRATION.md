# Evidence Registry Integration

> **Milestone 9** · Evidence requirements for reportable metrics / KPIs

## Service

`EvidenceRegistryService.get_requirements_for_metric(namespace)` returns seeded `cim_evidence_requirements` with mandatory/optional split and `readiness_status`:

* `declared` — requirements exist
* `not_applicable` — none seeded
* `unknown` — lookup failed / no session

## Examples

PUE / WUE / CUE (ISO/IEC 30134) and workflow energy (PROV-O / RO-Crate). Operational metrics without seeds (e.g. node power) return empty / `not_applicable`.
