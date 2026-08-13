# CIM Registry Design Summary

> Research packaging · Milestone 15

## Problem

Operational sustainability telemetry for research infrastructures arrives as heterogeneous raw keys, units, and vendor metrics. A file-based mapping cache cannot support governed alignment to ISO/EN KPIs, lifecycle stages, evidence, or provenance.

## Design

The GreenDIGIT CIM is a **registry-driven** information model: eleven additive `cim_*` registries (Metric, Unit, Source, Asset, Standards, Mapping, Lifecycle, Rule, Evidence, Provenance, Extension) plus orchestration, admin review, and explicit PUE/WUE/CUE calculation.

Core properties:

1. **Canonical namespaces** (`cim:…`) with quantity kind and canonical unit.
2. **Registry-first mapping** from raw keys, with legacy fallback — candidates are not auto-approved.
3. **Conservative standards relations** (`exactMatch` only when seeded/reviewed).
4. **RILM stage links** for a small curated set of metrics.
5. **Evidence requirements** declared per metric/standard; fulfillment tracking is still limited.
6. **Provenance** of orchestration, review, and KPI calculation.
7. **Export layer** (JSON, CSV, partial JSON-LD, RO-Crate-style, DCAT-style) for dissemination without replacing the internal model.

## What the demonstrator shows

- Known metrics resolve to CIM namespaces with unit validation.
- Unknown metrics become extension candidates.
- Reportable PUE is calculated only with valid energy inputs, period, and boundary.
- Exports preserve review status and do not upgrade candidates to approved.

## Implementation locus

Python services under `cloud_metrics/registry/`, SQLAlchemy `cim_*` tables, FastAPI under `/api/v1/cim-*`, Streamlit admin portal, pytest against in-memory SQLite + Alembic.

Further reading: `docs/target/REGISTRY_DRIVEN_CIM_FINAL_ARCHITECTURE.md`, `docs/target/CIM_REGISTRY_IMPLEMENTATION_SUMMARY.md`.
