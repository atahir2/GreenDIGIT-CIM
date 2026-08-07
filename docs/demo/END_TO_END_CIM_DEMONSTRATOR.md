# End-to-End Registry-Driven CIM Demonstrator

> **Milestone 10** · Integration validation of the full registry-driven CIM flow

## Purpose

Prove that realistic metric inputs can travel from raw sample → Registry Orchestrator → normalized CIM output with:

| Capability | Registry / component |
|------------|----------------------|
| Mapping | Mapping + Metric Registries (registry-first, legacy fallback retained) |
| Unit validation | Unit Registry + quantity kind |
| Source / asset resolution | Source + Asset Registries |
| Lifecycle stages | Lifecycle Registry |
| Standards mappings | Standards Registry |
| Governance rules | Rule Registry |
| Evidence requirements | Evidence Registry |
| Provenance | Provenance Registry |
| Unknown metrics | Extension Registry |

This milestone **does not** rewrite ingestion, remove legacy fallback, or introduce a calculation engine.

## Ingestion path

1. Demo / tests load fixtures from `tests/fixtures/cim_demo/`.
2. Demo mappings (`node_power_watts` → `cim:compute.node.power.draw`, …) are ensured in-session.
3. Each metric is passed to `RegistryOrchestratorService.process(RawMetricContext)`.
4. Production path (unchanged): `unified_ingestion` → `process_metric_sample(..., use_registry_orchestrator=True)` (opt-in flag on lower-level mapper).

## Scenarios

| ID | Fixture | Focus |
|----|---------|-------|
| A | `known_metrics_sample.json` | Known operational metrics |
| B | `wrong_units_sample.json` | Incompatible units |
| C | `workflow_run_metrics_sample.json` | Workflow reproducibility |
| D | `facility_kpi_sample.json` | Facility KPIs + PUE input preparation |
| E | `unknown_metrics_sample.json` | Extension candidates (fallback off) |
| — | `unstructured_metrics_sample.txt` | Existing unstructured parser only |

## How to run

See [DEMO_RUN_INSTRUCTIONS.md](DEMO_RUN_INSTRUCTIONS.md).

```bash
python -m cloud_metrics.scripts.run_cim_demo
pytest tests/test_cim_end_to_end_demo.py -q
```

## Operational registries (Milestone 10)

All 11 registries are operational for soft enrichment:

1. Metric · 2. Mapping · 3. Unit · 4. Source · 5. Asset  
6. Lifecycle · 7. Standards · 8. Rule · 9. Evidence · 10. Provenance · 11. Extension

## Legacy fallback

- **Retained** for scenarios A–D and production lookup (`use_fallback=True` default).
- Scenario E intentionally disables fallback so fuzzy alias matches (e.g. `work` inside `workflow_green_score`) cannot silently assign a CIM namespace; extension candidates are created instead.

## Known limitations

- No full PUE/WUE/CUE calculation engine — Scenario D prepares inputs and retrieves PUE evidence/standards.
- Demo raw→CIM mappings are created by the demonstrator helper (not permanent seed catalogue changes).
- Unstructured sample is parsed only; it is not fully orchestrated end-to-end.
- Admin UI review queues for extension candidates remain out of scope.
