# CIM Limitations and Future Work

> Research packaging · Milestone 15

## Implemented but bounded

| Area | Bound |
|------|--------|
| Standards alignment | Seeded relations only; few `exactMatch` rows |
| JSON-LD | Partial context; placeholder `cim:` IRIs; no SHACL |
| RO-Crate | Style/ready metadata object, not a validated crate on disk |
| DCAT | Style catalogue JSON, not DCAT-AP |
| PROV-O | JSON records + light JSON-LD pointers, not RDF |
| Evidence | Requirements declared; fulfillment not persisted unless the caller supplies it at export time |
| KPI | PUE / WUE / CUE only; not a generic formula engine |
| Ingestion validation | Soft warnings; reportable KPI calculation is the hard-block path |
| UI | Admin portal covers browse/review/KPI/provenance; no export download tab yet |

## Not claimed

- Certification against ISO/IEC 30134, EN 50600, or ISO 140xx
- Completeness of QUDT, SAREF, SOSA/SSN, or schema.org mappings
- Interoperability with arbitrary FAIR Digital Object / EOSC profiles
- Production replacement of legacy mapping JSON or partner `gd.*` export

## Recommended future work

1. Evidence **fulfillment** store and mark-complete UI for mandatory PUE/WUE/CUE evidence.
2. Validated RO-Crate 1.1 directory writer (files + metadata) and optional Process Run Crate profile.
3. DCAT-AP SHACL validation and real distribution URLs per RI.
4. RDF/Turtle export and a published CIM namespace IRI (replace `https://example.org/greendigit/cim#`).
5. Wire KPI calculation into the facility demo runner.
6. Promote stable demo mappings into seed after review.
7. Optional export tab on the admin portal (files only; still call `ExportService`).
8. Dual-run observability then deprecate duplicate legacy mapping paths.

## Honest citation guidance

Cite the CIM as a **registry-driven demonstrator** with conservative crosswalks and **partial** semantic exports. Do not cite JSON-LD / RO-Crate-style / DCAT-style outputs as certified Linked Open Data without independent validation.
