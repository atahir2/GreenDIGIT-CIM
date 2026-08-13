#!/usr/bin/env python
"""CLI: calculate reportable PUE / WUE / CUE (Milestone 13).

Uses configured SessionLocal so Unit / Evidence / Provenance registries apply.

Examples::

    python -m cloud_metrics.scripts.calculate_kpi pue --facility 1200 --it 800 --unit-energy kWh --period monthly --boundary facility
    python -m cloud_metrics.scripts.calculate_kpi wue --water 2.5 --water-unit m3 --it 800 --period monthly --boundary facility
    python -m cloud_metrics.scripts.calculate_kpi cue --carbon 250 --carbon-unit kgCO2e --it 800 --period monthly --boundary facility
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from cloud_metrics.registry.kpi import get_kpi_calculation_service
from cloud_metrics.registry.seed import seed_all
from cloud_metrics.utils.config import SessionLocal


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Calculate reportable CIM KPIs")
    parser.add_argument("kpi", choices=["pue", "wue", "cue"])
    parser.add_argument("--facility", type=float, default=None, help="Total facility energy")
    parser.add_argument("--it", type=float, required=True, help="IT equipment energy")
    parser.add_argument("--unit-energy", default="kWh")
    parser.add_argument("--water", type=float, default=None)
    parser.add_argument("--water-unit", default="L")
    parser.add_argument("--carbon", type=float, default=None)
    parser.add_argument("--carbon-unit", default="kgCO2e")
    parser.add_argument("--carbon-kind", choices=["emission", "intensity"], default="emission")
    parser.add_argument("--period", dest="aggregation_period", required=True)
    parser.add_argument("--boundary", required=True)
    parser.add_argument("--allow-candidate", action="store_true")
    parser.add_argument("--seed-first", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    with SessionLocal() as session:
        if args.seed_first:
            seed_all(session, commit=True)
        svc = get_kpi_calculation_service(session)
        common = dict(
            aggregation_period=args.aggregation_period,
            boundary=args.boundary,
            allow_candidate_inputs=args.allow_candidate,
        )
        if args.kpi == "pue":
            if args.facility is None:
                parser.error("pue requires --facility")
            result = svc.calculate_pue(
                {"name": "total_facility_energy", "value": args.facility, "unit": args.unit_energy},
                {"name": "it_equipment_energy", "value": args.it, "unit": args.unit_energy},
                **common,
            )
        elif args.kpi == "wue":
            if args.water is None:
                parser.error("wue requires --water")
            result = svc.calculate_wue(
                {"name": "water_usage_total", "value": args.water, "unit": args.water_unit},
                {"name": "it_equipment_energy", "value": args.it, "unit": args.unit_energy},
                **common,
            )
        else:
            if args.carbon is None:
                parser.error("cue requires --carbon")
            result = svc.calculate_cue(
                {
                    "name": "carbon_emission_operational"
                    if args.carbon_kind == "emission"
                    else "carbon_intensity",
                    "value": args.carbon,
                    "unit": args.carbon_unit,
                },
                {"name": "it_equipment_energy", "value": args.it, "unit": args.unit_energy},
                carbon_kind=args.carbon_kind,
                **common,
            )
        session.commit()

    payload = result.to_dict()
    if args.json:
        print(json.dumps(payload, indent=2, default=str))
    else:
        print(
            f"{result.kpi_namespace} status={result.calculation_status} "
            f"value={result.value} {result.unit} approved={result.reportable_approved}"
        )
        if result.errors:
            print("errors:", result.errors)
        if result.warnings:
            print("warnings:", result.warnings)
        print("provenance:", result.provenance_record_id)
    return 0 if result.calculation_status in {"calculated", "under_review"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
