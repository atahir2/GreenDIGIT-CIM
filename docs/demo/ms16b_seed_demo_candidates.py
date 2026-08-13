"""Seed safe MS16B demo candidates via registry services (not raw SQL).

Creates marked demo rows only (source keys / raw names start with ms16b.demo.).
Does not approve anything and does not touch canonical seed files.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from cloud_metrics.utils.config import SessionLocal  # noqa: E402
from cloud_metrics.registry.mapping import get_mapping_registry_service  # noqa: E402
from cloud_metrics.registry.mapping.types import MappingEntry  # noqa: E402
from cloud_metrics.registry.extension import get_extension_registry_service  # noqa: E402
from cloud_metrics.registry.review import get_admin_review_service  # noqa: E402


def main() -> int:
    out = {"mappings": [], "extensions": [], "pending_sample": []}
    with SessionLocal() as session:
        map_svc = get_mapping_registry_service(session)
        ext_svc = get_extension_registry_service(session)

        # Approve-path demo mapping → seeded approved metric
        m1 = map_svc.propose(
            MappingEntry(
                source_key="ms16b.demo.approve_power",
                cim_namespace="cim:compute.node.power.draw",
                relation_type="closeMatch",
                confidence=0.85,
                status="candidate",
                review_status="under_review",
                origin="ms16b_demo",
                rationale="MS16B demo candidate for approve action",
            )
        )
        out["mappings"].append({"source_key": m1.source_key, "id": m1.id, "role": "approve"})

        # Reject-path demo mapping
        m2 = map_svc.propose(
            MappingEntry(
                source_key="ms16b.demo.reject_wue",
                cim_namespace="cim:energy.efficiency.wue",
                relation_type="closeMatch",
                confidence=0.4,
                status="candidate",
                review_status="under_review",
                origin="ms16b_demo",
                rationale="MS16B demo candidate for reject action",
            )
        )
        out["mappings"].append({"source_key": m2.source_key, "id": m2.id, "role": "reject"})

        # Merge-path demo mapping (wrong target initially; UI merges to power.draw)
        m3 = map_svc.propose(
            MappingEntry(
                source_key="ms16b.demo.merge_cpu",
                cim_namespace="cim:compute.cpu.utilisation",
                relation_type="closeMatch",
                confidence=0.7,
                status="candidate",
                review_status="under_review",
                origin="ms16b_demo",
                rationale="MS16B demo candidate for merge action",
            )
        )
        out["mappings"].append({"source_key": m3.source_key, "id": m3.id, "role": "merge"})

        # Incomplete extension (approve should fail without metadata)
        e1 = ext_svc.propose_from_raw(
            "ms16b.demo.incomplete_extension",
            justification=None,  # placeholder path
            suggested_unit=None,
        )
        out["extensions"].append(
            {"raw": e1.raw_metric_name, "id": e1.id, "role": "incomplete_approve_fail"}
        )

        # Complete-enough extension (approve with UI edits / justification)
        e2 = ext_svc.propose_from_raw(
            "ms16b.demo.complete_extension",
            justification="Unknown/unresolved metric during orchestration",
            suggested_unit="score",
            source_context={"tool": "ms16b_demo", "file": "demo"},
        )
        out["extensions"].append(
            {"raw": e2.raw_metric_name, "id": e2.id, "role": "complete_approve_ok"}
        )

        # Reject-path extension
        e3 = ext_svc.propose_from_raw(
            "ms16b.demo.reject_extension",
            justification="MS16B demo extension for reject",
        )
        out["extensions"].append(
            {"raw": e3.raw_metric_name, "id": e3.id, "role": "reject"}
        )

        session.commit()

        review = get_admin_review_service(session)
        pending = review.list_pending()
        demo = [
            {
                "entity_type": e.entity_type.value,
                "entity_id": e.entity_id,
                "key": e.namespace_or_key,
                "status": e.status,
                "review_status": e.review_status,
            }
            for e in pending
            if (e.namespace_or_key or "").startswith("ms16b.demo")
            or "ms16b.demo" in (e.namespace_or_key or "")
            or "ms16b_demo" in (e.label or "")
        ]
        # Also catch extension namespaces containing ms16b
        if not demo:
            demo = [
                {
                    "entity_type": e.entity_type.value,
                    "entity_id": e.entity_id,
                    "key": e.namespace_or_key,
                    "status": e.status,
                    "review_status": e.review_status,
                }
                for e in pending
                if "ms16b" in str(e.namespace_or_key or "").lower()
                or "ms16b" in str(e.label or "").lower()
                or "ms16b" in str(getattr(e, "raw_metric_name", "") or "").lower()
            ]
        out["pending_demo_count"] = len(demo)
        out["pending_sample"] = demo[:20]
        out["pending_total"] = len(pending)

    print(json.dumps(out, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
