# Extension Registry Integration

> **Milestone 9** · Unknown / non-standard metrics as extension candidates

## Service

`ExtensionRegistryService.propose_from_raw` creates (or returns) a candidate:

* Suggested namespace `cim:extension.<slug>`
* Candidate `CimMetricDefinition` + `CimExtensionMetric`
* `status=candidate`, `review_status=under_review`
* Never treated as approved (`is_approved` false until explicit catalogue promotion)

Deduplicates by suggested namespace / raw key. Placeholders: `approve` (accepted + under_review), `reject`, `merge`, `update`.
