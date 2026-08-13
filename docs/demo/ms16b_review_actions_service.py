"""MS16B companion: demo review actions via AdminReviewService (same path as UI).

Used when Streamlit select automation is flaky. Does NOT raw-SQL mutate cim_*.
Writes provenance IDs for the validation log.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from cloud_metrics.utils.config import SessionLocal  # noqa: E402
from cloud_metrics.ui.cim_portal import perform_review_action  # noqa: E402
from cloud_metrics.registry.review import ReviewEntityType, get_admin_review_service  # noqa: E402
from cloud_metrics.models.cim_registry import CimProvenanceRecord, CimMetricMapping, CimExtensionMetric  # noqa: E402


OUT = ROOT / "docs" / "demo" / "logs" / "ms16b" / "review_actions_service.json"


def _find_mapping(session, source_key: str):
    return (
        session.query(CimMetricMapping)
        .filter(CimMetricMapping.source_key == source_key)
        .order_by(CimMetricMapping.id.desc())
        .first()
    )


def _find_extension_by_ns_fragment(session, fragment: str):
    pending = get_admin_review_service(session).list_pending(
        entity_types=[ReviewEntityType.EXTENSION]
    )
    for e in pending:
        key = str(e.namespace_or_key or "")
        if key.endswith(fragment) or f"_{fragment}" in key or key == fragment:
            return e
    # also search all extensions via list without queue filter using namespace contains exact demo token
    for e in pending:
        key = str(e.namespace_or_key or "")
        if f"ms16b_demo_{fragment}" in key or f"ms16b.demo.{fragment}" in key:
            return e
    return None


def main() -> int:
    results = {"actions": []}
    with SessionLocal() as session:
        # Approve mapping
        m = _find_mapping(session, "ms16b.demo.approve_power")
        if m and (m.status or "").lower() in {"candidate", "pending", "under_review"}:
            d = perform_review_action(
                session, "mapping", m.id, "approve", reviewer="ms16b_admin",
                notes="MS16B service companion approve",
            )
            results["actions"].append({"action": "approve_mapping", "id": m.id, **d.to_dict()})
        elif m:
            results["actions"].append({"action": "approve_mapping", "skipped": True, "status": m.status, "id": m.id})

        # Promote approved mapping
        m = _find_mapping(session, "ms16b.demo.approve_power")
        if m and (m.review_status or "").lower() == "approved":
            d = perform_review_action(
                session, "mapping", m.id, "promote_to_seed", reviewer="ms16b_admin",
                notes="MS16B promote demo",
            )
            results["actions"].append({"action": "promote_to_seed", "id": m.id, **d.to_dict()})

        # Reject mapping
        m = _find_mapping(session, "ms16b.demo.reject_wue")
        if m and (m.status or "").lower() not in {"rejected", "approved"}:
            d = perform_review_action(
                session, "mapping", m.id, "reject", reviewer="ms16b_admin",
                notes="MS16B service companion reject",
            )
            results["actions"].append({"action": "reject_mapping", "id": m.id, **d.to_dict()})

        # Merge mapping
        m = _find_mapping(session, "ms16b.demo.merge_cpu")
        if m and (m.status or "").lower() in {"candidate", "pending", "under_review"}:
            d = perform_review_action(
                session, "mapping", m.id, "merge", reviewer="ms16b_admin",
                notes="MS16B service companion merge",
                merge_target_namespace="cim:compute.node.power.draw",
            )
            results["actions"].append({"action": "merge_mapping", "id": m.id, **d.to_dict()})

        # Incomplete extension approve should fail
        e = _find_extension_by_ns_fragment(session, "incomplete_extension")
        if e:
            d = perform_review_action(
                session, "extension", e.entity_id, "approve", reviewer="ms16b_admin",
                notes="should fail",
            )
            results["actions"].append(
                {"action": "incomplete_extension_approve", "id": e.entity_id, **d.to_dict()}
            )

        # Complete extension with full edits (UI cannot send all fields today)
        e = _find_extension_by_ns_fragment(session, "complete_extension")
        if e:
            d = perform_review_action(
                session,
                "extension",
                e.entity_id,
                "approve",
                reviewer="ms16b_admin",
                notes="MS16B complete extension approve",
                edits={
                    "justification": "Research KPI for GreenDIGIT pilot; reviewed by domain owner",
                    "quantity_kind": "Dimensionless",
                    "suggested_unit": "score",
                    "suggested_definition": "Pilot green score for workflow scheduling",
                    "source_context": {"tool": "ms16b_demo"},
                },
            )
            results["actions"].append(
                {"action": "complete_extension_approve", "id": e.entity_id, **d.to_dict()}
            )

        # Reject extension
        e = _find_extension_by_ns_fragment(session, "reject_extension")
        if e:
            d = perform_review_action(
                session, "extension", e.entity_id, "reject", reviewer="ms16b_admin",
                notes="MS16B reject extension",
            )
            results["actions"].append(
                {"action": "reject_extension", "id": e.entity_id, **d.to_dict()}
            )

        # Collect recent review_action provenance
        prov = (
            session.query(CimProvenanceRecord)
            .filter(CimProvenanceRecord.activity == "review_action")
            .order_by(CimProvenanceRecord.id.desc())
            .limit(15)
            .all()
        )
        results["recent_review_provenance"] = [
            {
                "id": r.id,
                "entity_type": r.entity_type,
                "entity_id": r.entity_id,
                "agent": r.agent,
                "notes": r.notes,
            }
            for r in prov
        ]

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
    print(json.dumps(results, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
