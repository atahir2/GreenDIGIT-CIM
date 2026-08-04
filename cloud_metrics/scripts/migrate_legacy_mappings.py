"""CLI: migrate legacy metric mappings into ``cim_metric_*`` registries.

Usage:
    python -m cloud_metrics.scripts.migrate_legacy_mappings
    python -m cloud_metrics.scripts.migrate_legacy_mappings --dry-run
"""

from __future__ import annotations

import argparse
import json
import logging
import sys

from cloud_metrics.registry.migration import (
    discover_legacy_mappings,
    migrate_legacy_mappings,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Migrate legacy raw→unified mappings into cim_metric_mappings"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Discover and print counts without writing to the database",
    )
    parser.add_argument(
        "--seed-first",
        action="store_true",
        help="Run Milestone 3 seed_all() before migration so approved metrics exist",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable INFO logging",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )

    discovery = discover_legacy_mappings()
    print(
        json.dumps(
            {
                "discovered_unique": len(discovery.records),
                "skipped_noise": discovery.skipped_noise,
                "skipped_uncategorized": discovery.skipped_uncategorized,
                "by_source": discovery.by_source,
            },
            indent=2,
        )
    )

    if args.dry_run:
        sample = [
            {
                "raw_key": r.raw_key,
                "legacy_unified_key": r.legacy_unified_key,
                "source_name": r.source_name,
                "confidence": r.confidence,
            }
            for r in discovery.records[:20]
        ]
        print(json.dumps({"sample": sample}, indent=2))
        return 0

    from cloud_metrics.registry.seed import seed_all
    from cloud_metrics.utils.config import SessionLocal

    with SessionLocal() as session:
        if args.seed_first:
            seed_report = seed_all(session, commit=True)
            print("seed:", seed_report.as_dict())
        report = migrate_legacy_mappings(session, discovery=discovery, commit=True)
        print(json.dumps(report.as_dict(), indent=2))
        if report.errors:
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
