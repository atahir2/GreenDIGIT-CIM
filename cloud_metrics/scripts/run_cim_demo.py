#!/usr/bin/env python
"""CLI: run Milestone 10 registry-driven CIM end-to-end demonstrator.

Uses an in-memory SQLite CIM registry (migration + seed) by default so the
demo does not require a live database. Pass ``--use-db`` to use SessionLocal.

Examples::

    python -m cloud_metrics.scripts.run_cim_demo
    python -m cloud_metrics.scripts.run_cim_demo --scenario A
    python -m cloud_metrics.scripts.run_cim_demo --json
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from cloud_metrics.demo.cim_demonstrator import (
    SAMPLE_FILES,
    dumps_report,
    run_all_scenarios,
    run_scenario,
)
from cloud_metrics.registry.seed import seed_all

M2_FILE = (
    _PROJECT_ROOT
    / "migrations"
    / "versions"
    / "c2f8a1b9e047_add_cim_registry_tables.py"
)


def _load_m2():
    spec = importlib.util.spec_from_file_location("cim_m2_migration_demo", M2_FILE)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _memory_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    migration = _load_m2()
    with engine.begin() as conn:
        ctx = MigrationContext.configure(conn)
        with Operations.context(ctx):
            migration.upgrade()
    Session = sessionmaker(bind=engine, future=True)
    session = Session()
    seed_all(session, commit=True)
    return session, engine, migration


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run registry-driven CIM end-to-end demonstrator (Milestone 10)."
    )
    parser.add_argument(
        "--scenario",
        choices=sorted(SAMPLE_FILES.keys()) + ["all"],
        default="all",
        help="Scenario letter A–E, or all (default)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON report",
    )
    parser.add_argument(
        "--use-db",
        action="store_true",
        help="Use configured SessionLocal instead of in-memory SQLite",
    )
    args = parser.parse_args(argv)

    session = None
    engine = None
    migration = None
    try:
        if args.use_db:
            from cloud_metrics.utils.config import SessionLocal

            session = SessionLocal()
            seed_all(session, commit=True)
        else:
            session, engine, migration = _memory_session()

        if args.scenario == "all":
            report = run_all_scenarios(session)
            if args.json:
                print(dumps_report(report))
            else:
                print("=== GreenDIGIT Registry-Driven CIM Demonstrator (Milestone 10) ===")
                print(f"Fixtures: {report['fixture_dir']}")
                print()
                for key, scen in report["scenarios"].items():
                    print(f"--- Scenario {key}: {scen.get('description')} ---")
                    for summary in scen.get("summaries") or []:
                        print(summary)
                        print()
                    if "pue_preparation" in scen:
                        print("  [PUE preparation]")
                        print(scen["pue_preparation"]["summary"])
                        print()
                if report.get("unstructured"):
                    print("--- Optional unstructured sample ---")
                    print(json.dumps(report["unstructured"], indent=2))
        else:
            report = run_scenario(session, args.scenario)
            if args.json:
                print(dumps_report(report))
            else:
                print(f"=== Scenario {report['scenario']} ===")
                print(report.get("description") or "")
                print()
                for summary in report.get("summaries") or []:
                    print(summary)
                    print()
                if "pue_preparation" in report:
                    print("[PUE preparation]")
                    print(report["pue_preparation"]["summary"])
        return 0
    finally:
        if session is not None:
            session.close()
        if engine is not None and migration is not None:
            with engine.begin() as conn:
                ctx = MigrationContext.configure(conn)
                with Operations.context(ctx):
                    migration.downgrade()


if __name__ == "__main__":
    raise SystemExit(main())
