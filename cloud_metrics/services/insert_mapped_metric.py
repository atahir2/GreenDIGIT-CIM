# cloud_metrics/services/insert_mapped_metric.py
from __future__ import annotations

from typing import List, Optional
from sqlalchemy import func
from sqlalchemy.orm import Session

from cloud_metrics.models.metric_definition import MetricDefinition
from cloud_metrics.utils.config import SessionLocal
from cloud_metrics.utils.mapping_sync import sync_metric_mapping
from cloud_metrics.utils.unified_key import to_gd


def insert_mapped_metric(
    *,
    unified_key: str,
    source_keys: Optional[List[str]] = None,
    tags: Optional[List[str]] = None,
) -> int:
    """
    Ensure a MetricDefinition exists for the given unified_key, merge sources/tags,
    sync raw->unified in metric_mapping.json, and attach standards.
    Returns the metric_definition.id.
    """
    uk = to_gd(unified_key)

    # normalize inputs
    src_in = sorted({*(source_keys or [])})
    tags_in = sorted({*(tags or [])})

    with SessionLocal() as session:  # type: Session
        # case-insensitive lookup
        metric: Optional[MetricDefinition] = (
            session.query(MetricDefinition)
            .filter(func.lower(MetricDefinition.unified_key) == uk.lower())
            .first()
        )

        if metric:
            # merge sources/tags idempotently
            existing_sources = set(metric.sources or [])
            existing_tags = set(metric.tags or [])
            metric.sources = sorted(existing_sources.union(src_in))
            metric.tags = sorted(existing_tags.union(tags_in))
            session.commit()
            # print(f" Updated metric definition: {uk}")
        else:
            metric = MetricDefinition(
                unified_key=uk,
                sources=src_in,
                tags=tags_in,
            )
            session.add(metric)
            session.commit()
            # print(f" Inserted metric definition: {uk}")

        # Keep JSON mapping in sync (raw -> unified)
        # Use the *raw* keys as provided in source_keys (may be empty)
        for raw_key in src_in:
            try:
                sync_metric_mapping(uk, raw_key)
            except Exception as e:
                # don't block ingestion on json sync
                print(f"[mapping_sync] JSON sync failed for {raw_key} → {uk}: {e}")

        # ---- Standards Hook (idempotent) ----
        try:
            from cloud_metrics.services.standards_registry import attach_standard
            attach_standard(uk)
        except Exception as e:
            # don't block ingestion on standards linkage
            print(f"[standards] attach skipped for {uk}: {e}")

        return metric.id
