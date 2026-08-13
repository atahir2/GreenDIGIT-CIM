"""Repair / inspect MS16B demo candidates."""
from __future__ import annotations

from cloud_metrics.utils.config import SessionLocal
from cloud_metrics.registry.mapping import get_mapping_registry_service
from cloud_metrics.registry.mapping.types import MappingEntry
from cloud_metrics.registry.review import get_admin_review_service
from cloud_metrics.models.cim_registry import CimExtensionMetric


def main() -> None:
    with SessionLocal() as s:
        m = get_mapping_registry_service(s).propose(
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
        s.commit()
        print("reject_mapping_id", m.id)

        exts = (
            s.query(CimExtensionMetric)
            .filter(CimExtensionMetric.raw_metric_name.like("ms16b.demo%"))
            .all()
        )
        for e in exts:
            print(
                "ext",
                e.id,
                e.raw_metric_name,
                e.status,
                e.review_status,
                e.metric_id,
            )

        pending = get_admin_review_service(s).list_pending()
        print("pending_total", len(pending))
        for e in pending:
            parts = [
                e.entity_type.value,
                str(e.entity_id),
                str(e.namespace_or_key or ""),
                str(e.label or ""),
            ]
            blob = "|".join(parts)
            if "ms16b" in blob.lower():
                print("DEMO", blob, e.status, e.review_status)


if __name__ == "__main__":
    main()
