# Rule Registry Integration

> **Milestone 9** · Declarative validation during orchestration

## Service

`RuleRegistryService` evaluates seeded `cim_validation_rules` against an orchestration payload and returns structured `ValidationResult` objects (`passed`, `severity`, `message`, `details`).

Severities: `info` | `warning` | `error` | `critical`.

## Behaviour

* Soft: results populate orchestrator `validation_results` / `governance_warnings` / `governance_errors`
* Does not abort ingestion
* Legacy `validate_metric_sample` (string list on `gd.*`) remains unchanged

## Seeded rules applied

Namespace required · numeric unit (unless dimensionless) · observed needs timestamp+source · calculated needs formula · energy power/energy distinction · KPI period+boundary · workflow reproducibility context · extension justification
