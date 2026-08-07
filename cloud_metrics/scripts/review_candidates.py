#!/usr/bin/env python
"""CLI: admin review of CIM registry candidates (Milestone 12).

Examples::

    python -m cloud_metrics.scripts.review_candidates list
    python -m cloud_metrics.scripts.review_candidates list --type mapping
    python -m cloud_metrics.scripts.review_candidates approve mapping 12 --reviewer alice
    python -m cloud_metrics.scripts.review_candidates reject extension 3 --reviewer alice --notes \"needs unit\"
    python -m cloud_metrics.scripts.review_candidates merge mapping 12 --target cim:compute.node.power.draw --reviewer alice
    python -m cloud_metrics.scripts.review_candidates promote mapping 12 --reviewer alice
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from cloud_metrics.registry.review import (
    ReviewAction,
    ReviewEntityType,
    get_admin_review_service,
)
from cloud_metrics.registry.seed import seed_all
from cloud_metrics.utils.config import SessionLocal


def _print(obj, as_json: bool) -> None:
    if as_json:
        print(json.dumps(obj, indent=2, default=str))
    else:
        print(obj)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="CIM admin candidate review CLI")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument(
        "--seed-first",
        action="store_true",
        help="Idempotently seed cim_* catalogues before acting",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list", help="List pending/candidate/under_review entries")
    p_list.add_argument(
        "--type",
        dest="entity_type",
        choices=[e.value for e in ReviewEntityType],
        action="append",
        help="Filter entity type (repeatable)",
    )

    p_get = sub.add_parser("get", help="Get one reviewable entry")
    p_get.add_argument("entity_type", choices=[e.value for e in ReviewEntityType])
    p_get.add_argument("entity_id", type=int)

    def _action_parser(name: str, help_text: str):
        p = sub.add_parser(name, help=help_text)
        p.add_argument("entity_type", choices=[e.value for e in ReviewEntityType])
        p.add_argument("entity_id", type=int)
        p.add_argument("--reviewer", required=True)
        p.add_argument("--notes", default=None)
        return p

    p_approve = _action_parser("approve", "Approve a candidate")
    p_approve.add_argument(
        "--allow-exact-match",
        action="store_true",
        help="Required to approve standards mapping as exactMatch",
    )
    p_approve.add_argument(
        "--justification",
        default=None,
        help="Required real justification when approving extensions",
    )
    p_approve.add_argument("--quantity-kind", default=None)
    p_approve.add_argument("--unit", default=None)
    p_approve.add_argument("--source-context", default=None)

    _action_parser("reject", "Reject a candidate")
    _action_parser("deprecate", "Deprecate an approved entry")
    _action_parser("reopen", "Reopen a rejected entry to under_review")
    _action_parser("mark-under-review", "Mark candidate as under_review")

    p_merge = _action_parser("merge", "Merge candidate into approved metric namespace")
    p_merge.add_argument("--target", required=True, help="Target cim:* namespace")

    p_promote = _action_parser("promote", "Export approved entry to seed proposal files")
    p_promote.add_argument(
        "--output-dir",
        default=None,
        help="Directory for seed promotion artifacts (default: generated/seed_promotion)",
    )

    args = parser.parse_args(argv)

    with SessionLocal() as session:
        if args.seed_first:
            seed_all(session, commit=True)
        svc = get_admin_review_service(session)

        if args.command == "list":
            entries = svc.list_pending(entity_types=args.entity_type)
            _print([e.to_dict() for e in entries], args.json)
            if not args.json:
                print(f"\n{len(entries)} pending/reviewable entr(y/ies)")
            return 0

        if args.command == "get":
            entry = svc.get_entry(args.entity_type, args.entity_id)
            if entry is None:
                print("not found", file=sys.stderr)
                return 1
            _print(entry.to_dict(), args.json)
            return 0

        action_map = {
            "approve": ReviewAction.APPROVE,
            "reject": ReviewAction.REJECT,
            "deprecate": ReviewAction.DEPRECATE,
            "reopen": ReviewAction.REOPEN,
            "mark-under-review": ReviewAction.MARK_UNDER_REVIEW,
            "merge": ReviewAction.MERGE,
            "promote": ReviewAction.PROMOTE_TO_SEED,
        }
        action = action_map[args.command]
        edits = {}
        if args.command == "approve":
            if args.justification:
                edits["justification"] = args.justification
            if args.quantity_kind:
                edits["quantity_kind"] = args.quantity_kind
            if args.unit:
                edits["suggested_unit"] = args.unit
            if args.source_context:
                edits["source_context"] = args.source_context

        decision = svc.apply(
            args.entity_type,
            args.entity_id,
            action,
            reviewer=args.reviewer,
            notes=args.notes,
            edits=edits or None,
            merge_target_namespace=getattr(args, "target", None),
            allow_exact_match=bool(getattr(args, "allow_exact_match", False)),
            seed_output_dir=Path(args.output_dir) if getattr(args, "output_dir", None) else None,
        )
        _print(decision.to_dict(), args.json)
        return 0 if decision.ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
