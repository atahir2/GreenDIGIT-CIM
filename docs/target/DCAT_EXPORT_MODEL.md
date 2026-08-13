# DCAT-style Export Model

> **Milestone 15** · **Partial** catalogue metadata

## Status

**DCAT-style**, not DCAT-AP / DCAT 3 / DCAT-US certified.

- Uses `dcat:`, `dct:`, `foaf:` prefixes
- Emits Catalog → Dataset → Distribution
- Publisher and access URL default to **placeholders** unless the caller supplies them
- Metric variables are listed as `dcat:theme` objects (CIM namespaces), not as a formal RDF Data Cube / STAT-DCAT vocabulary

Profile: `dcat-style`. `compliance.full_standards_compliance` = `false`.

## Catalogue contents

| DCAT-ish field | CIM source / default |
|----------------|----------------------|
| `dct:title` | Request title or “GreenDIGIT CIM metric catalogue” |
| `dct:description` | Request description or registry summary |
| `dct:publisher` | Request publisher or “Research Infrastructure (placeholder)” |
| `dcat:dataset` | One dataset for the metric catalogue / reporting set |
| `dcat:distribution` | JSON and CSV distribution stubs |
| `dcat:service` / `dcat:endpointURL` | `access_endpoint` or API placeholder |
| Metric variables | Catalogue namespaces, labels, units, quantity kinds |
| `dct:temporal` | Optional start/end from the request |
| Standards mappings | Attached under `cim:standardsMappings` on the dataset |

## What is future work

- DCAT-AP 2.x / 3.0 SHACL validation
- Real distribution URLs and checksums
- Geo / language / licence / rights metadata
- One dataset per reporting period or per RI site

## API

```text
GET /api/v1/cim-export/dcat-style?publisher=Example%20RI&access_endpoint=https://ri.example/cim
POST /api/v1/cim-export/dcat-style
```
