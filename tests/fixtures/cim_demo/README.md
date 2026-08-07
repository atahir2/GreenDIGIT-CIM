# CIM End-to-End Demo Fixtures

Realistic sample inputs for Milestone 10 registry-driven CIM demonstrator.

| File | Scenario |
|------|----------|
| `known_metrics_sample.json` | A — known operational metrics |
| `wrong_units_sample.json` | B — intentionally wrong units |
| `workflow_run_metrics_sample.json` | C — workflow reproducibility |
| `facility_kpi_sample.json` | D — facility KPI / PUE inputs |
| `unknown_metrics_sample.json` | E — extension candidates |
| `unstructured_metrics_sample.txt` | Optional — existing unstructured parser |

Run via:

```bash
python -m cloud_metrics.scripts.run_cim_demo
pytest tests/test_cim_end_to_end_demo.py -q
```
