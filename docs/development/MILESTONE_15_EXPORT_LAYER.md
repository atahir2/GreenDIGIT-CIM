# Milestone 15 — Export, Interoperability, and Research Packaging

Read-only export layer over CIM registries: JSON, CSV, partial JSON-LD, RO-Crate-style, DCAT-style, standards crosswalk, evidence readiness, provenance. Internal registry model unchanged. Semantic formats labelled partial where full compliance is not implemented.

## Deliverables

| Artifact | Path |
|----------|------|
| Service | `cloud_metrics/registry/export/` |
| CLI | `cloud_metrics/scripts/export_cim.py` |
| API | `/api/v1/cim-export/*` |
| Tests | `tests/test_cim_export_service.py` |
| Docs | `docs/target/EXPORT_*.md`, `JSONLD_*`, `ROCRATE_*`, `DCAT_*`, `STANDARDS_CROSSWALK_*`, `PROVENANCE_EXPORT_*`, `LEGACY_EXPORT_HANDLING.md` |
| Demo | `docs/demo/EXPORT_DEMO_GUIDE.md` |
| Research | `docs/research/CIM_*.md` |

## Non-goals

Replace `external_json.py` · full RO-Crate 1.1 crates · DCAT-AP certification · RDF/Turtle · evidence fulfillment store · export UI tab
