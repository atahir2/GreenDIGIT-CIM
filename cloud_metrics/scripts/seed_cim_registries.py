#!/usr/bin/env python
"""CLI entry point: seed additive ``cim_*`` registry tables (Milestone 3).

Idempotent. Does not modify ingestion, legacy tables, or mapping JSON files.

Example::

    python -m cloud_metrics.scripts.seed_cim_registries
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Ensure project root on path when executed as a script
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from cloud_metrics.registry.seed import seed_all
from cloud_metrics.utils.config import SessionLocal


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Seed Milestone 3 cim_* registry catalogues (idempotent)."
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print SeedReport as JSON",
    )
    args = parser.parse_args(argv)

    with SessionLocal() as session:
        report = seed_all(session, commit=True)

    if args.json:
        print(json.dumps(report.as_dict(), indent=2))
    else:
        print("Milestone 3 CIM registry seed complete.")
        print("Created:", report.created)
        print("Already present:", report.existing)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
