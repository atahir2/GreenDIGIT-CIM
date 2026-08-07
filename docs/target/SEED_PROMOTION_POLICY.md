# Seed Promotion Policy

> **Milestone 12**

## Rule

`promote_to_seed` writes **proposal artifacts only**. It never edits:

- `cloud_metrics/registry/seed/data.py`
- migration sync catalogues
- production DB seed rows automatically beyond the already-approved entity

## Preconditions

- Entry `status` is `approved` or `active`
- Entry `review_status` is `approved`

## Outputs (default directory `generated/seed_promotion/`)

| File | Purpose |
|------|---------|
| `seed_promotion_report.json` | Latest machine-readable report |
| `generated_seed_candidates.json` | Mapping/metric/extension slices |
| `SEED_PROMOTION_CANDIDATES.md` | Human review table |
| Timestamped copies | Audit history |

A convenience copy may also be referenced from docs; generated files are local artifacts.

## Manual follow-up

A human reviews the proposal and, if accepted, updates seed data or migration mappings in a **separate** change.
