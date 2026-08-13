#!/usr/bin/env python
"""CLI: export CIM registry data (Milestone 15).

Examples::

    python -m cloud_metrics.scripts.export_cim json --out registry.json
    python -m cloud_metrics.scripts.export_cim csv mappings --out mappings.csv
    python -m cloud_metrics.scripts.export_cim jsonld --namespace cim:energy.efficiency.pue
    python -m cloud_metrics.scripts.export_cim rocrate --workflow-id wf-204 --run-id run-2026-001 --energy 0.42 --carbon 0.12
    python -m cloud_metrics.scripts.export_cim dcat
    python -m cloud_metrics.scripts.export_cim crosswalk --out crosswalk.json
    python -m cloud_metrics.scripts.export_cim evidence --namespace cim:energy.efficiency.pue
    python -m cloud_metrics.scripts.export_cim provenance
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from cloud_metrics.registry.export import (
    CSV_DATASETS,
    DcatExportRequest,
    WorkflowRunExportRequest,
    get_export_service,
)
from cloud_metrics.registry.seed import seed_all
from cloud_metrics.utils.config import SessionLocal


def _write(payload, out: str | None, *, csv_text: bool = False) -> None:
    if csv_text:
        text = payload if isinstance(payload, str) else str(payload)
    else:
        text = json.dumps(payload, indent=2, ensure_ascii=False, default=str)
    if out:
        Path(out).write_text(text, encoding="utf-8")
        print(out)
    else:
        print(text)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export CIM registry data")
    parser.add_argument(
        "format",
        choices=[
            "json",
            "csv",
            "jsonld",
            "rocrate",
            "dcat",
            "crosswalk",
            "evidence",
            "provenance",
        ],
    )
    parser.add_argument(
        "dataset",
        nargs="?",
        default="metrics",
        help="CSV dataset: metrics|mappings|standards|evidence|extensions",
    )
    parser.add_argument("--out", default=None)
    parser.add_argument("--namespace", default=None)
    parser.add_argument("--entity-type", default=None)
    parser.add_argument("--entity-id", type=int, default=None)
    parser.add_argument("--workflow-id", default="wf-204")
    parser.add_argument("--run-id", default="run-2026-001")
    parser.add_argument("--energy", type=float, default=None)
    parser.add_argument("--carbon", type=float, default=None)
    parser.add_argument("--duration", type=float, default=None)
    parser.add_argument("--source", default=None)
    parser.add_argument("--asset", default=None)
    parser.add_argument("--publisher", default=None)
    parser.add_argument("--access-endpoint", default=None)
    parser.add_argument("--seed-first", action="store_true")
    args = parser.parse_args(argv)

    with SessionLocal() as session:
        if args.seed_first:
            seed_all(session, commit=True)
        svc = get_export_service(session)
        fmt = args.format
        if fmt == "json":
            _write(svc.export_json(), args.out)
        elif fmt == "csv":
            try:
                text = svc.export_csv(args.dataset)
            except ValueError as exc:
                parser.error(str(exc) + f" (datasets: {CSV_DATASETS})")
                return 2
            _write(text, args.out, csv_text=True)
        elif fmt == "jsonld":
            _write(svc.export_jsonld(metric_namespace=args.namespace), args.out)
        elif fmt == "rocrate":
            req = WorkflowRunExportRequest(
                workflow_id=args.workflow_id,
                workflow_run_id=args.run_id,
                energy_per_run=args.energy,
                carbon_per_run=args.carbon,
                duration_seconds=args.duration,
                source=args.source,
                asset=args.asset,
                publisher=args.publisher,
            )
            _write(svc.export_rocrate_style(req), args.out)
        elif fmt == "dcat":
            req = DcatExportRequest(
                publisher=args.publisher,
                access_endpoint=args.access_endpoint,
            )
            _write(svc.export_dcat_style(req), args.out)
        elif fmt == "crosswalk":
            _write(svc.export_standards_crosswalk(), args.out)
        elif fmt == "evidence":
            _write(
                svc.export_evidence_readiness(metric_namespace=args.namespace),
                args.out,
            )
        else:
            _write(
                svc.export_provenance(
                    entity_type=args.entity_type, entity_id=args.entity_id
                ),
                args.out,
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
