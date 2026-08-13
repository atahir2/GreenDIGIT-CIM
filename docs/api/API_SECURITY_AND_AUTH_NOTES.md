# API Security and Auth Notes

> **Milestone 16C** · Current state and production recommendations  
> This milestone does **not** implement production auth. Notes only.

## Current local / demo posture

| Control | Status |
|---------|--------|
| Authentication | **None** — FastAPI endpoints are open on localhost |
| Authorization / RBAC | **None** — reviewer string is client-supplied |
| TLS | Local HTTP only |
| Multi-tenant isolation | `organization_id` is a payload field, not an enforced tenancy boundary |
| Rate limiting | None |
| Request signing | None |
| Secrets | `.env` for DB / Influx; not used for API tokens |

Acceptable for local validation and research demos. **Not acceptable for internet-facing production.**

## Recommended production controls

1. **Mutual TLS or OAuth2 / OIDC** for organization clients (client credentials per RI).
2. **Map token → `organization_id`** server-side; ignore or override client-supplied org id when mismatched.
3. **RBAC**:
   - `ingest` role: POST `/api/v1/cim-ingest/metrics`
   - `reviewer` role: `/api/v1/cim-review/*`
   - `exporter` role: `/api/v1/cim-export/*`
4. **Separate network planes**: ingest edge vs admin review vs export.
5. **Audit**: retain `organization_id`, client id, and provenance ids for every ingest and review action (already partially covered by CIM provenance).
6. **Rate limits / payload size caps** on ingest.
7. **Disable** `/api/v1/cim-ingest/scenarios/*` outside demo environments.
8. **Do not** expose legacy `/api/v1/registry/*/approve` without the same authz as Admin Review.
9. **Input hygiene**: reject oversized `source_metadata` / `extra` blobs; sanitize strings stored in provenance.
10. **Secrets**: rotate DB and Influx credentials; never embed tokens in sample payloads.

## What not to do

- Auto-approve mappings based on client identity alone
- Trust client `reviewer` strings without authenticated identity
- Put production CIM on a public IP without TLS + auth
- Use demo `ensure_demo_mappings=true` as a production bootstrap for untrusted orgs (use reviewed Mapping Registry rows instead)

## Interim (staging)

If staging must be shared:

- Put FastAPI behind a reverse proxy with basic auth or IP allow-list
- Restrict CORS to known frontends
- Keep Admin Portal on a separate host/VPN
