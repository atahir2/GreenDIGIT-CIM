"""Seed promotion helpers — export approved review items; never auto-edit seed data."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from cloud_metrics.registry.review.types import SeedPromotionItem

DEFAULT_OUTPUT_DIR = Path("generated") / "seed_promotion"


def ensure_output_dir(path: Optional[Path] = None) -> Path:
    out = path or DEFAULT_OUTPUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    return out


def write_seed_promotion_report(
    items: Sequence[SeedPromotionItem],
    *,
    output_dir: Optional[Path] = None,
    reviewer: Optional[str] = None,
    notes: Optional[str] = None,
) -> Dict[str, str]:
    """Write JSON + markdown proposal files. Does not modify ``registry/seed/data.py``."""
    out = ensure_output_dir(output_dir)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "reviewer": reviewer,
        "notes": notes,
        "auto_applied_to_canonical_seed": False,
        "items": [
            {
                "kind": i.kind,
                "source_key": i.source_key,
                "cim_namespace": i.cim_namespace,
                "relation_type": i.relation_type,
                "origin": i.origin,
                "entity_id": i.entity_id,
                "notes": i.notes,
                "payload": i.payload,
            }
            for i in items
        ],
    }
    json_path = out / f"seed_promotion_report_{stamp}.json"
    candidates_path = out / f"generated_seed_candidates_{stamp}.json"
    md_path = out / f"SEED_PROMOTION_CANDIDATES_{stamp}.md"

    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    candidates_path.write_text(
        json.dumps({"mappings": [i for i in payload["items"] if i["kind"] == "mapping"],
                    "metrics": [i for i in payload["items"] if i["kind"] == "metric"],
                    "extensions": [i for i in payload["items"] if i["kind"] == "extension"]},
                   indent=2),
        encoding="utf-8",
    )

    lines = [
        "# Seed Promotion Candidates",
        "",
        f"Generated: `{payload['generated_at']}`",
        f"Reviewer: `{reviewer or 'unknown'}`",
        "",
        "> **Not applied automatically.** Review and manually update "
        "`cloud_metrics/registry/seed/data.py` or migration sync if accepted.",
        "",
        "| Kind | Source key | CIM namespace | Relation | Origin | Entity id |",
        "|------|------------|--------------|----------|--------|-----------|",
    ]
    for i in items:
        lines.append(
            f"| {i.kind} | {i.source_key or ''} | {i.cim_namespace or ''} | "
            f"{i.relation_type or ''} | {i.origin or ''} | {i.entity_id or ''} |"
        )
    if notes:
        lines.extend(["", "## Notes", "", notes])
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # Stable latest pointers (overwrite)
    (out / "seed_promotion_report.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )
    (out / "generated_seed_candidates.json").write_text(
        candidates_path.read_text(encoding="utf-8"), encoding="utf-8"
    )
    (out / "SEED_PROMOTION_CANDIDATES.md").write_text(
        md_path.read_text(encoding="utf-8"), encoding="utf-8"
    )

    return {
        "report_json": str(json_path),
        "candidates_json": str(candidates_path),
        "markdown": str(md_path),
        "latest_report": str(out / "seed_promotion_report.json"),
        "latest_markdown": str(out / "SEED_PROMOTION_CANDIDATES.md"),
    }
