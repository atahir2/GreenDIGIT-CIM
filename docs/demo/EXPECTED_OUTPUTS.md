# Expected Outputs (Overview)

Detailed scenario notes:

- [EXPECTED_KNOWN_METRIC_OUTPUT.md](EXPECTED_KNOWN_METRIC_OUTPUT.md)
- [EXPECTED_WRONG_UNIT_OUTPUT.md](EXPECTED_WRONG_UNIT_OUTPUT.md)
- [EXPECTED_WORKFLOW_OUTPUT.md](EXPECTED_WORKFLOW_OUTPUT.md)
- [EXPECTED_EXTENSION_METRIC_OUTPUT.md](EXPECTED_EXTENSION_METRIC_OUTPUT.md)

## Compact checklist

| Scenario | Mapping | Unit | Enrichment | Governance |
|----------|---------|------|------------|------------|
| A known | `cim:compute.node.power.draw` (registry) | valid Power/W | source, asset, lifecycle, standards (contextual/inputToKPI) | provenance; no critical silent failure |
| B wrong unit | same CIM ns possible | **incompatible** | provenance records issue | warnings / rule failures |
| C workflow | `cim:workflow.energy.per_run` | valid Energy/kWh | reproducibility + PROV-O/RO-Crate | evidence requirements |
| D facility | facility + IT energy; PUE prepared | valid | PUE exactMatch ISO/EN if seeded | PUE evidence |
| E unknown | unresolved | n/a | extension candidate | review_status under_review/candidate; no approved standards |

IDs for source/asset/provenance/extension are session-local and may vary between runs.
