# Seeded Validation and Evidence Rules

> **Milestone 3** · Declarative seeds in ``cim_validation_rules`` and ``cim_evidence_requirements``

These rows are **data only**. Rule engines / evidence workflows are not enforced at runtime in this milestone.

---

## Validation rules (`cim_validation_rules`)

| Name | Severity | Target | Intent |
|------|----------|--------|--------|
| `metric_requires_namespace` | error | metric | Namespace required |
| `numeric_metric_requires_unit` | error | metric | Unit required unless Dimensionless |
| `observed_metric_requires_timestamp_and_source` | error | metric | Observed samples need timestamp + source |
| `calculated_metric_requires_derivation` | warning | metric | Calculated / KPI / derived need formula or method |
| `energy_distinguishes_power_vs_energy` | error | metric | Power vs Energy quantity/unit consistency |
| `kpi_requires_period_and_boundary` | warning | metric | KPIs need aggregation period + boundary |
| `workflow_reproducibility_requires_run_context` | warning | metric | Workflow reproducibility needs run context |
| `extension_metric_requires_justification` | error | extension | Extensions need justification + review_status |

Conditions are stored as JSON in `condition` for later evaluation by the Rule Registry service.

---

## Evidence requirements (`cim_evidence_requirements`)

| Metric | Standard | Evidence type | Level | Boundary / period |
|--------|----------|---------------|-------|-------------------|
| `cim:energy.efficiency.pue` | ISO-IEC-30134 | calculation | mandatory | facility / monthly_or_annual |
| `cim:energy.efficiency.pue` | ISO-IEC-30134 | measurement | mandatory | facility_and_it |
| `cim:energy.efficiency.wue` | ISO-IEC-30134 | measurement | mandatory | site_or_facility |
| `cim:energy.efficiency.cue` | ISO-IEC-30134 | calculation | mandatory | facility |
| `cim:workflow.energy.per_run` | PROV-O | audit | recommended | workflow_run / per_run |
| `cim:workflow.energy.per_run` | RO-CRATE | document | recommended | workflow_run / per_run |

PUE description covers facility energy, IT energy, aggregation period, boundary, and metering source.  
Workflow energy evidence covers run ID, time window, resource allocation, calculation method, and provenance.
