"""Admin Review service — Milestone 12.

Controlled review of candidate / under_review registry entries.
Does not auto-approve. Does not modify canonical seed files automatically.
Preserves ingestion / orchestrator behavior.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union

from sqlalchemy.orm import Session

from cloud_metrics.registry.provenance import ProvenanceRegistryService
from cloud_metrics.registry.review.seed_promotion import write_seed_promotion_report
from cloud_metrics.registry.review.transitions import (
    assert_transition_allowed,
    is_approved_status,
    is_queue_status,
    normalize_status,
    review_status_for_action,
)
from cloud_metrics.registry.review.types import (
    QUEUE_STATUSES,
    ReviewAction,
    ReviewDecision,
    ReviewEntityType,
    ReviewError,
    ReviewableEntry,
    SeedPromotionItem,
)

logger = logging.getLogger(__name__)

_PLACEHOLDER_JUSTIFICATIONS = frozenset(
    {
        "placeholder justification pending review",
        "unknown/unresolved metric during orchestration",
    }
)


class AdminReviewService:
    """Central admin review workflow for CIM registry candidates."""

    def __init__(self, session: Optional[Session] = None) -> None:
        self._session = session
        self._prov = ProvenanceRegistryService(session=session)

    # ------------------------------------------------------------------
    # Listing / detail
    # ------------------------------------------------------------------

    def list_pending(
        self,
        *,
        entity_types: Optional[Sequence[Union[str, ReviewEntityType]]] = None,
        include_accepted: bool = True,
    ) -> List[ReviewableEntry]:
        """List candidate / pending / under_review (and accepted) entries."""
        if self._session is None:
            return []
        wanted = self._normalize_types(entity_types)
        out: List[ReviewableEntry] = []
        if ReviewEntityType.MAPPING in wanted:
            out.extend(self._list_mappings(queue_only=True, standards_only=False))
        if ReviewEntityType.STANDARDS_MAPPING in wanted:
            out.extend(self._list_mappings(queue_only=True, standards_only=True))
        if ReviewEntityType.EXTENSION in wanted:
            out.extend(self._list_extensions(queue_only=True, include_accepted=include_accepted))
        if ReviewEntityType.METRIC in wanted:
            out.extend(self._list_metrics(queue_only=True))
        if ReviewEntityType.SOURCE in wanted:
            out.extend(self._list_sources(queue_only=True))
        if ReviewEntityType.ASSET in wanted:
            out.extend(self._list_assets(queue_only=True))
        if ReviewEntityType.UNIT in wanted:
            out.extend(self._list_units(queue_only=True))
        if ReviewEntityType.LIFECYCLE_LINK in wanted:
            out.extend(self._list_lifecycle_links(queue_only=True))
        return out

    def get_entry(
        self,
        entity_type: Union[str, ReviewEntityType],
        entity_id: int,
    ) -> Optional[ReviewableEntry]:
        et = ReviewEntityType(entity_type)
        if et == ReviewEntityType.MAPPING:
            return self._mapping_entry(entity_id, standards_only=False)
        if et == ReviewEntityType.STANDARDS_MAPPING:
            return self._mapping_entry(entity_id, standards_only=True)
        if et == ReviewEntityType.EXTENSION:
            return self._extension_entry(entity_id)
        if et == ReviewEntityType.METRIC:
            return self._metric_entry(entity_id)
        if et == ReviewEntityType.SOURCE:
            return self._source_entry(entity_id)
        if et == ReviewEntityType.ASSET:
            return self._asset_entry(entity_id)
        if et == ReviewEntityType.UNIT:
            return self._unit_entry(entity_id)
        if et == ReviewEntityType.LIFECYCLE_LINK:
            return self._lifecycle_entry(entity_id)
        return None

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def apply(
        self,
        entity_type: Union[str, ReviewEntityType],
        entity_id: int,
        action: Union[str, ReviewAction],
        *,
        reviewer: str,
        notes: Optional[str] = None,
        edits: Optional[Dict[str, Any]] = None,
        merge_target_namespace: Optional[str] = None,
        allow_exact_match: bool = False,
        seed_output_dir: Optional[Path] = None,
        commit: bool = True,
    ) -> ReviewDecision:
        et = ReviewEntityType(entity_type)
        act = ReviewAction(action)
        entry = self.get_entry(et, entity_id)
        if entry is None:
            return ReviewDecision(
                ok=False,
                action=act,
                entity_type=et,
                entity_id=entity_id,
                reviewer=reviewer,
                notes=notes,
                message="entity not found",
                errors=["entity not found"],
            )

        prev_status = entry.status
        prev_review = entry.review_status

        try:
            if act == ReviewAction.EDIT:
                decision = self._edit(
                    et, entity_id, entry, reviewer=reviewer, notes=notes, edits=edits or {}
                )
            elif act == ReviewAction.APPROVE:
                decision = self._approve(
                    et,
                    entity_id,
                    entry,
                    reviewer=reviewer,
                    notes=notes,
                    edits=edits or {},
                    allow_exact_match=allow_exact_match,
                )
            elif act == ReviewAction.REJECT:
                decision = self._simple_status_change(
                    et, entity_id, entry, act, reviewer=reviewer, notes=notes
                )
            elif act == ReviewAction.MARK_UNDER_REVIEW:
                decision = self._simple_status_change(
                    et, entity_id, entry, act, reviewer=reviewer, notes=notes
                )
            elif act == ReviewAction.REQUEST_CHANGES:
                decision = self._simple_status_change(
                    et, entity_id, entry, act, reviewer=reviewer, notes=notes
                )
            elif act == ReviewAction.REOPEN:
                decision = self._simple_status_change(
                    et, entity_id, entry, act, reviewer=reviewer, notes=notes
                )
            elif act == ReviewAction.DEPRECATE:
                decision = self._simple_status_change(
                    et, entity_id, entry, act, reviewer=reviewer, notes=notes
                )
            elif act == ReviewAction.MERGE:
                decision = self._merge(
                    et,
                    entity_id,
                    entry,
                    reviewer=reviewer,
                    notes=notes,
                    target_namespace=merge_target_namespace,
                )
            elif act == ReviewAction.PROMOTE_TO_SEED:
                decision = self._promote_to_seed(
                    et,
                    entity_id,
                    entry,
                    reviewer=reviewer,
                    notes=notes,
                    output_dir=seed_output_dir,
                )
            else:
                raise ReviewError(f"unsupported action: {act}")
        except (ReviewError, ValueError) as exc:
            errors = list(getattr(exc, "errors", None) or [str(exc)])
            decision = ReviewDecision(
                ok=False,
                action=act,
                entity_type=et,
                entity_id=entity_id,
                previous_status=prev_status,
                previous_review_status=prev_review,
                reviewer=reviewer,
                notes=notes,
                message=str(exc),
                errors=errors,
            )

        if decision.ok:
            decision.previous_status = prev_status
            decision.previous_review_status = prev_review
            decision.entry = self.get_entry(et, entity_id)
            if decision.entry is not None:
                decision.new_status = decision.entry.status
                decision.new_review_status = decision.entry.review_status
            prov_id = self._record_provenance(decision)
            decision.provenance_record_id = prov_id
            if commit and self._session is not None:
                self._session.commit()
        elif self._session is not None and commit:
            self._session.rollback()

        return decision

    # Convenience wrappers
    def approve(self, entity_type, entity_id, *, reviewer: str, **kwargs) -> ReviewDecision:
        return self.apply(entity_type, entity_id, ReviewAction.APPROVE, reviewer=reviewer, **kwargs)

    def reject(self, entity_type, entity_id, *, reviewer: str, **kwargs) -> ReviewDecision:
        return self.apply(entity_type, entity_id, ReviewAction.REJECT, reviewer=reviewer, **kwargs)

    def merge(
        self,
        entity_type,
        entity_id,
        *,
        reviewer: str,
        merge_target_namespace: str,
        **kwargs,
    ) -> ReviewDecision:
        return self.apply(
            entity_type,
            entity_id,
            ReviewAction.MERGE,
            reviewer=reviewer,
            merge_target_namespace=merge_target_namespace,
            **kwargs,
        )

    def promote_to_seed(
        self, entity_type, entity_id, *, reviewer: str, **kwargs
    ) -> ReviewDecision:
        return self.apply(
            entity_type, entity_id, ReviewAction.PROMOTE_TO_SEED, reviewer=reviewer, **kwargs
        )

    # ------------------------------------------------------------------
    # Action implementations
    # ------------------------------------------------------------------

    def _simple_status_change(
        self,
        et: ReviewEntityType,
        entity_id: int,
        entry: ReviewableEntry,
        action: ReviewAction,
        *,
        reviewer: str,
        notes: Optional[str],
    ) -> ReviewDecision:
        target = assert_transition_allowed(entry.status, action)
        rs = review_status_for_action(action, target)
        self._set_row_status(et, entity_id, status=target, review_status=rs, notes=notes, reviewer=reviewer)
        return ReviewDecision(
            ok=True,
            action=action,
            entity_type=et,
            entity_id=entity_id,
            reviewer=reviewer,
            notes=notes,
            message=f"{action.value} applied → {target}",
            new_status=target,
            new_review_status=rs,
        )

    def _edit(
        self,
        et: ReviewEntityType,
        entity_id: int,
        entry: ReviewableEntry,
        *,
        reviewer: str,
        notes: Optional[str],
        edits: Dict[str, Any],
    ) -> ReviewDecision:
        assert_transition_allowed(entry.status, ReviewAction.EDIT)
        self._apply_edits(et, entity_id, edits)
        if notes:
            self._append_notes(et, entity_id, notes, reviewer=reviewer)
        # Rejected + edit does not auto-reopen; caller must REOPEN
        return ReviewDecision(
            ok=True,
            action=ReviewAction.EDIT,
            entity_type=et,
            entity_id=entity_id,
            reviewer=reviewer,
            notes=notes,
            message="metadata updated",
            extras={"edits": edits},
        )

    def _approve(
        self,
        et: ReviewEntityType,
        entity_id: int,
        entry: ReviewableEntry,
        *,
        reviewer: str,
        notes: Optional[str],
        edits: Dict[str, Any],
        allow_exact_match: bool,
    ) -> ReviewDecision:
        assert_transition_allowed(entry.status, ReviewAction.APPROVE)

        if et == ReviewEntityType.EXTENSION:
            self._validate_extension_approval(entity_id, edits=edits)
        if et in {ReviewEntityType.MAPPING, ReviewEntityType.STANDARDS_MAPPING}:
            self._validate_mapping_approval(
                entity_id,
                standards=(et == ReviewEntityType.STANDARDS_MAPPING),
                allow_exact_match=allow_exact_match,
                edits=edits,
            )
        if et == ReviewEntityType.METRIC:
            self._validate_metric_approval(entity_id)

        if edits:
            self._apply_edits(et, entity_id, edits)

        self._set_row_status(
            et,
            entity_id,
            status="approved",
            review_status="approved",
            notes=notes,
            reviewer=reviewer,
            set_approved_fields=True,
        )

        # Extension: also approve linked metric definition
        if et == ReviewEntityType.EXTENSION:
            self._approve_extension_metric_definition(entity_id, reviewer=reviewer)

        return ReviewDecision(
            ok=True,
            action=ReviewAction.APPROVE,
            entity_type=et,
            entity_id=entity_id,
            reviewer=reviewer,
            notes=notes,
            message="approved",
            new_status="approved",
            new_review_status="approved",
        )

    def _merge(
        self,
        et: ReviewEntityType,
        entity_id: int,
        entry: ReviewableEntry,
        *,
        reviewer: str,
        notes: Optional[str],
        target_namespace: Optional[str],
    ) -> ReviewDecision:
        if et not in {ReviewEntityType.MAPPING, ReviewEntityType.EXTENSION}:
            raise ReviewError("merge is only supported for mapping or extension")
        if not target_namespace:
            raise ReviewError("merge_target_namespace is required")

        assert_transition_allowed(entry.status, ReviewAction.MERGE)

        from cloud_metrics.models.cim_registry import (
            CimExtensionMetric,
            CimMetricDefinition,
            CimMetricMapping,
        )

        target = (
            self._session.query(CimMetricDefinition)
            .filter_by(namespace=target_namespace)
            .one_or_none()
        )
        if target is None:
            raise ReviewError(f"target namespace not found: {target_namespace}")
        if not is_approved_status(target.status) or normalize_status(target.review_status) != "approved":
            raise ReviewError(
                f"merge target must be an approved metric: {target_namespace}"
            )

        if et == ReviewEntityType.MAPPING:
            row = self._session.get(CimMetricMapping, entity_id)
            if row is None:
                raise ReviewError("mapping not found")
            # Prevent duplicate approved mapping for same source_key
            dup = (
                self._session.query(CimMetricMapping)
                .filter(
                    CimMetricMapping.source_key == row.source_key,
                    CimMetricMapping.id != row.id,
                    CimMetricMapping.status.in_(("approved", "active")),
                )
                .first()
            )
            if dup is not None and dup.metric_id != target.id:
                raise ReviewError(
                    "duplicate approved mapping exists for this source_key "
                    f"(id={dup.id}); reject or deprecate it first"
                )
            if dup is not None and dup.metric_id == target.id:
                # Candidate is redundant — mark merged/rejected
                row.status = "merged"
                row.review_status = "approved"
                row.notes = self._note_join(
                    row.notes, f"merged_into_existing_mapping_id={dup.id} by {reviewer}"
                )
            else:
                row.metric_id = target.id
                row.status = "approved"
                row.review_status = "approved"
                row.approved_by = reviewer
                row.approved_at = datetime.now(timezone.utc)
                row.notes = self._note_join(
                    row.notes,
                    f"merged_into_namespace={target_namespace} by {reviewer}",
                )
            if notes:
                row.notes = self._note_join(row.notes, notes)
            self._session.flush()
        else:
            row = self._session.get(CimExtensionMetric, entity_id)
            if row is None:
                raise ReviewError("extension not found")
            row.status = "merged"
            row.review_status = "approved"
            row.reviewed_at = datetime.now(timezone.utc)
            row.notes = self._note_join(
                row.notes, f"merged_into={target_namespace} by {reviewer}"
            )
            if notes:
                row.notes = self._note_join(row.notes, notes)
            # Keep linked metric as candidate/rejected — do not auto-approve extension ns
            metric = self._session.get(CimMetricDefinition, row.metric_id)
            if metric is not None:
                metric.status = "merged"
                metric.review_status = "approved"
                metric.notes = self._note_join(
                    metric.notes, f"merged_into={target_namespace}"
                )
            self._session.flush()

        return ReviewDecision(
            ok=True,
            action=ReviewAction.MERGE,
            entity_type=et,
            entity_id=entity_id,
            reviewer=reviewer,
            notes=notes,
            message=f"merged into {target_namespace}",
            extras={"merge_target_namespace": target_namespace},
        )

    def _promote_to_seed(
        self,
        et: ReviewEntityType,
        entity_id: int,
        entry: ReviewableEntry,
        *,
        reviewer: str,
        notes: Optional[str],
        output_dir: Optional[Path],
    ) -> ReviewDecision:
        if not is_approved_status(entry.status):
            raise ReviewError(
                "promote_to_seed requires an approved (or active) entry; approve first"
            )
        if normalize_status(entry.review_status) != "approved":
            raise ReviewError("promote_to_seed requires review_status=approved")

        item = self._to_seed_item(et, entity_id, entry)
        paths = write_seed_promotion_report(
            [item],
            output_dir=output_dir,
            reviewer=reviewer,
            notes=notes,
        )
        # Append audit note on entity
        self._append_notes(
            et,
            entity_id,
            f"promoted_to_seed_proposal={paths.get('latest_report')} by {reviewer}",
            reviewer=reviewer,
        )
        return ReviewDecision(
            ok=True,
            action=ReviewAction.PROMOTE_TO_SEED,
            entity_type=et,
            entity_id=entity_id,
            reviewer=reviewer,
            notes=notes,
            message="seed proposal written (canonical seed not modified)",
            seed_proposal_path=paths.get("latest_report"),
            extras=paths,
        )

    # ------------------------------------------------------------------
    # Validation helpers
    # ------------------------------------------------------------------

    def _validate_extension_approval(
        self, extension_id: int, *, edits: Dict[str, Any]
    ) -> None:
        from cloud_metrics.models.cim_registry import CimExtensionMetric, CimMetricDefinition

        row = self._session.get(CimExtensionMetric, extension_id)
        if row is None:
            raise ReviewError("extension not found")
        metric = self._session.get(CimMetricDefinition, row.metric_id)
        if metric is None:
            raise ReviewError("extension metric definition missing")

        justification = edits.get("justification") or row.justification or ""
        if not justification.strip():
            raise ReviewError("extension approval requires justification")
        if justification.strip().lower() in _PLACEHOLDER_JUSTIFICATIONS and not edits.get(
            "justification"
        ):
            raise ReviewError(
                "extension approval requires a real justification "
                "(placeholder text is not sufficient)"
            )

        # Unit / quantity kind: from metric columns or edits / notes
        has_qk = metric.quantity_kind_id is not None or edits.get("quantity_kind") or edits.get(
            "quantity_kind_id"
        )
        has_unit = metric.canonical_unit_id is not None or edits.get("canonical_unit") or edits.get(
            "canonical_unit_id"
        ) or edits.get("suggested_unit")
        notes = (row.notes or "") + " " + (metric.notes or "")
        if "suggested_unit=" in notes or "suggested_quantity_kind=" in notes:
            has_unit = has_unit or ("suggested_unit=" in notes)
            has_qk = has_qk or ("suggested_quantity_kind=" in notes)
        if not (has_qk or has_unit):
            raise ReviewError(
                "extension approval requires quantity kind and/or canonical/suggested unit"
            )

        # Source context / definition
        has_def = bool(metric.description) or bool(edits.get("suggested_definition"))
        has_source_ctx = bool(edits.get("source_context")) or "source_context=" in notes
        if not has_def:
            raise ReviewError("extension approval requires a metric definition/description")
        if not has_source_ctx and not edits.get("skip_source_context_check"):
            # Allow if justification explicitly provided in this approval call
            if not edits.get("justification"):
                raise ReviewError(
                    "extension approval requires source context "
                    "(pass edits.source_context or edits.justification with review notes)"
                )

    def _validate_mapping_approval(
        self,
        mapping_id: int,
        *,
        standards: bool,
        allow_exact_match: bool,
        edits: Dict[str, Any],
    ) -> None:
        from cloud_metrics.models.cim_registry import CimMetricDefinition, CimMetricMapping

        row = self._session.get(CimMetricMapping, mapping_id)
        if row is None:
            raise ReviewError("mapping not found")
        metric = self._session.get(CimMetricDefinition, row.metric_id)
        if metric is None:
            raise ReviewError("mapped metric definition missing")
        if not is_approved_status(metric.status):
            raise ReviewError(
                "cannot approve mapping to a non-approved metric; "
                "approve the metric first or merge into an approved namespace"
            )

        # Duplicate approved mapping prevention
        dup = (
            self._session.query(CimMetricMapping)
            .filter(
                CimMetricMapping.source_key == row.source_key,
                CimMetricMapping.id != row.id,
                CimMetricMapping.status.in_(("approved", "active")),
            )
            .first()
        )
        if dup is not None:
            raise ReviewError(
                f"duplicate approved mapping already exists for source_key={row.source_key!r} "
                f"(id={dup.id})"
            )

        relation = edits.get("relation_type") or row.relation_type or ""
        if standards or row.standard_id is not None:
            if relation == "exactMatch" and not allow_exact_match:
                raise ReviewError(
                    "standards mapping cannot become exactMatch without "
                    "explicit allow_exact_match=True from reviewer"
                )

    def _validate_metric_approval(self, metric_id: int) -> None:
        from cloud_metrics.models.cim_registry import CimMetricDefinition

        metric = self._session.get(CimMetricDefinition, metric_id)
        if metric is None:
            raise ReviewError("metric not found")
        if not metric.namespace:
            raise ReviewError("metric approval requires namespace")
        if metric.quantity_kind_id is None:
            raise ReviewError("metric approval requires quantity_kind_id")
        if metric.canonical_unit_id is None:
            raise ReviewError("metric approval requires canonical_unit_id")

    def _approve_extension_metric_definition(self, extension_id: int, *, reviewer: str) -> None:
        from cloud_metrics.models.cim_registry import CimExtensionMetric, CimMetricDefinition

        row = self._session.get(CimExtensionMetric, extension_id)
        if row is None:
            return
        metric = self._session.get(CimMetricDefinition, row.metric_id)
        if metric is None:
            return
        metric.status = "approved"
        metric.review_status = "approved"
        metric.notes = self._note_join(metric.notes, f"approved_via_extension_review by {reviewer}")
        row.reviewed_at = datetime.now(timezone.utc)
        self._session.flush()

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------

    def _set_row_status(
        self,
        et: ReviewEntityType,
        entity_id: int,
        *,
        status: str,
        review_status: str,
        notes: Optional[str],
        reviewer: str,
        set_approved_fields: bool = False,
    ) -> None:
        row = self._get_row(et, entity_id)
        if row is None:
            raise ReviewError("entity row not found")
        row.status = status
        row.review_status = review_status
        if notes:
            row.notes = self._note_join(row.notes, f"{notes} [{reviewer}]")
        if set_approved_fields and hasattr(row, "approved_by"):
            row.approved_by = reviewer
            row.approved_at = datetime.now(timezone.utc)
        if et == ReviewEntityType.EXTENSION and hasattr(row, "reviewed_at"):
            row.reviewed_at = datetime.now(timezone.utc)
        self._session.flush()

    def _append_notes(
        self, et: ReviewEntityType, entity_id: int, note: str, *, reviewer: str
    ) -> None:
        row = self._get_row(et, entity_id)
        if row is None:
            return
        row.notes = self._note_join(row.notes, f"{note} [{reviewer}]")
        self._session.flush()

    def _apply_edits(
        self, et: ReviewEntityType, entity_id: int, edits: Dict[str, Any]
    ) -> None:
        if not edits:
            return
        from cloud_metrics.models.cim_registry import (
            CimExtensionMetric,
            CimMetricDefinition,
            CimMetricMapping,
            CimQuantityKind,
            CimUnit,
        )

        row = self._get_row(et, entity_id)
        if row is None:
            raise ReviewError("entity row not found")

        if et in {ReviewEntityType.MAPPING, ReviewEntityType.STANDARDS_MAPPING}:
            for key in ("relation_type", "rationale", "origin", "confidence_score"):
                if key in edits and edits[key] is not None:
                    setattr(row, key, edits[key])
            if "notes" in edits and edits["notes"] is not None:
                row.notes = edits["notes"]
        elif et == ReviewEntityType.EXTENSION:
            for key in ("justification", "proposed_standard", "proposed_by", "confidence_score"):
                if key in edits and edits[key] is not None:
                    setattr(row, key, edits[key])
            metric = self._session.get(CimMetricDefinition, row.metric_id)
            if metric is not None:
                if edits.get("suggested_definition"):
                    metric.description = edits["suggested_definition"]
                if edits.get("suggested_domain"):
                    metric.domain = edits["suggested_domain"]
                if edits.get("suggested_category"):
                    metric.category = edits["suggested_category"]
                if edits.get("quantity_kind") or edits.get("quantity_kind_id"):
                    qk = None
                    if edits.get("quantity_kind_id"):
                        qk = self._session.get(CimQuantityKind, edits["quantity_kind_id"])
                    elif edits.get("quantity_kind"):
                        qk = (
                            self._session.query(CimQuantityKind)
                            .filter_by(name=edits["quantity_kind"])
                            .first()
                        )
                    if qk is not None:
                        metric.quantity_kind_id = qk.id
                if edits.get("canonical_unit") or edits.get("canonical_unit_id") or edits.get(
                    "suggested_unit"
                ):
                    unit = None
                    if edits.get("canonical_unit_id"):
                        unit = self._session.get(CimUnit, edits["canonical_unit_id"])
                    else:
                        sym = edits.get("canonical_unit") or edits.get("suggested_unit")
                        unit = (
                            self._session.query(CimUnit).filter_by(symbol=sym).first()
                            if sym
                            else None
                        )
                    if unit is not None:
                        metric.canonical_unit_id = unit.id
                if edits.get("source_context") is not None:
                    row.notes = self._note_join(
                        row.notes, f"source_context={edits['source_context']}"
                    )
        elif et == ReviewEntityType.METRIC:
            for key in (
                "label",
                "description",
                "domain",
                "category",
                "subcategory",
                "metric_type",
                "notes",
                "confidence_score",
            ):
                if key in edits and edits[key] is not None:
                    setattr(row, key, edits[key])
        elif et in {ReviewEntityType.SOURCE, ReviewEntityType.ASSET, ReviewEntityType.UNIT}:
            for key, val in edits.items():
                if hasattr(row, key) and val is not None and key not in {"id", "status", "review_status"}:
                    setattr(row, key, val)
        elif et == ReviewEntityType.LIFECYCLE_LINK:
            for key in ("relevance", "notes", "confidence_score"):
                if key in edits and edits[key] is not None:
                    setattr(row, key, edits[key])

        self._session.flush()

    def _get_row(self, et: ReviewEntityType, entity_id: int):
        from cloud_metrics.models.cim_registry import (
            CimAsset,
            CimExtensionMetric,
            CimMetricDefinition,
            CimMetricLifecycleLink,
            CimMetricMapping,
            CimSource,
            CimUnit,
        )

        model = {
            ReviewEntityType.MAPPING: CimMetricMapping,
            ReviewEntityType.STANDARDS_MAPPING: CimMetricMapping,
            ReviewEntityType.EXTENSION: CimExtensionMetric,
            ReviewEntityType.METRIC: CimMetricDefinition,
            ReviewEntityType.SOURCE: CimSource,
            ReviewEntityType.ASSET: CimAsset,
            ReviewEntityType.UNIT: CimUnit,
            ReviewEntityType.LIFECYCLE_LINK: CimMetricLifecycleLink,
        }.get(et)
        if model is None:
            return None
        return self._session.get(model, entity_id)

    def _record_provenance(self, decision: ReviewDecision) -> Optional[int]:
        if self._session is None:
            return None
        entry = self._prov.record_activity(
            entity_type=f"cim_{decision.entity_type.value}",
            entity_id=decision.entity_id,
            activity="review_action",
            agent=decision.reviewer or "admin_reviewer",
            method="AdminReviewService.apply",
            inputs={
                "action": decision.action.value,
                "previous_status": decision.previous_status,
                "previous_review_status": decision.previous_review_status,
            },
            outputs={
                "new_status": decision.new_status,
                "new_review_status": decision.new_review_status,
                "ok": decision.ok,
                "seed_proposal_path": decision.seed_proposal_path,
                "extras": decision.extras,
            },
            notes=decision.notes or decision.message,
        )
        return entry.id

    def _to_seed_item(
        self, et: ReviewEntityType, entity_id: int, entry: ReviewableEntry
    ) -> SeedPromotionItem:
        kind = {
            ReviewEntityType.MAPPING: "mapping",
            ReviewEntityType.STANDARDS_MAPPING: "mapping",
            ReviewEntityType.EXTENSION: "extension",
            ReviewEntityType.METRIC: "metric",
        }.get(et, et.value)
        return SeedPromotionItem(
            kind=kind,
            source_key=entry.namespace_or_key if et in {
                ReviewEntityType.MAPPING, ReviewEntityType.STANDARDS_MAPPING
            } else None,
            cim_namespace=entry.details.get("cim_namespace")
            or (entry.namespace_or_key if et in {ReviewEntityType.METRIC, ReviewEntityType.EXTENSION} else None),
            relation_type=entry.relation_type,
            origin=entry.origin,
            entity_id=entity_id,
            notes=entry.notes,
            payload=entry.to_dict(),
        )

    @staticmethod
    def _note_join(existing: Optional[str], addition: str) -> str:
        base = (existing or "").strip()
        if not base:
            return addition
        return f"{base}\n{addition}"

    def _normalize_types(
        self, entity_types: Optional[Sequence[Union[str, ReviewEntityType]]]
    ) -> List[ReviewEntityType]:
        if not entity_types:
            return list(ReviewEntityType)
        return [ReviewEntityType(t) for t in entity_types]

    # ------------------------------------------------------------------
    # List / get builders
    # ------------------------------------------------------------------

    def _list_mappings(self, *, queue_only: bool, standards_only: bool) -> List[ReviewableEntry]:
        from cloud_metrics.models.cim_registry import CimMetricMapping

        q = self._session.query(CimMetricMapping)
        if standards_only:
            q = q.filter(CimMetricMapping.standard_id.isnot(None))
        else:
            q = q.filter(CimMetricMapping.standard_id.is_(None))
        rows = q.all()
        out = []
        for row in rows:
            if queue_only and not (
                is_queue_status(row.status) or is_queue_status(row.review_status)
            ):
                continue
            et = (
                ReviewEntityType.STANDARDS_MAPPING
                if row.standard_id is not None
                else ReviewEntityType.MAPPING
            )
            entry = self._mapping_to_reviewable(row, et)
            if entry:
                out.append(entry)
        return out

    def _mapping_entry(self, entity_id: int, *, standards_only: bool) -> Optional[ReviewableEntry]:
        from cloud_metrics.models.cim_registry import CimMetricMapping

        row = self._session.get(CimMetricMapping, entity_id)
        if row is None:
            return None
        if standards_only and row.standard_id is None:
            return None
        if not standards_only and row.standard_id is not None:
            # still allow get as mapping
            pass
        et = (
            ReviewEntityType.STANDARDS_MAPPING
            if row.standard_id is not None
            else ReviewEntityType.MAPPING
        )
        return self._mapping_to_reviewable(row, et)

    def _mapping_to_reviewable(self, row, et: ReviewEntityType) -> ReviewableEntry:
        metric = getattr(row, "metric", None)
        return ReviewableEntry(
            entity_type=et,
            entity_id=row.id,
            status=row.status or "candidate",
            review_status=row.review_status or "pending",
            label=metric.label if metric is not None else None,
            namespace_or_key=row.source_key,
            origin=row.origin,
            relation_type=row.relation_type,
            notes=row.notes,
            created_by=row.created_by,
            confidence_score=row.confidence_score,
            details={
                "cim_namespace": metric.namespace if metric is not None else None,
                "metric_id": row.metric_id,
                "standard_id": row.standard_id,
                "approved_by": row.approved_by,
            },
        )

    def _list_extensions(self, *, queue_only: bool, include_accepted: bool) -> List[ReviewableEntry]:
        from cloud_metrics.models.cim_registry import CimExtensionMetric

        rows = self._session.query(CimExtensionMetric).all()
        out = []
        for row in rows:
            st = normalize_status(row.status)
            if queue_only and st not in QUEUE_STATUSES and not (
                include_accepted and st == "accepted"
            ):
                if not is_queue_status(row.review_status):
                    continue
            entry = self._extension_to_reviewable(row)
            if entry:
                out.append(entry)
        return out

    def _extension_entry(self, entity_id: int) -> Optional[ReviewableEntry]:
        from cloud_metrics.models.cim_registry import CimExtensionMetric

        row = self._session.get(CimExtensionMetric, entity_id)
        return self._extension_to_reviewable(row) if row else None

    def _extension_to_reviewable(self, row) -> ReviewableEntry:
        metric = getattr(row, "metric", None)
        return ReviewableEntry(
            entity_type=ReviewEntityType.EXTENSION,
            entity_id=row.id,
            status=row.status or "candidate",
            review_status=row.review_status or "under_review",
            label=metric.label if metric is not None else None,
            namespace_or_key=metric.namespace if metric is not None else None,
            justification=row.justification,
            notes=row.notes,
            created_by=row.created_by or row.proposed_by,
            confidence_score=row.confidence_score,
            details={
                "metric_id": row.metric_id,
                "proposed_standard": row.proposed_standard,
                "proposed_by": row.proposed_by,
            },
        )

    def _list_metrics(self, *, queue_only: bool) -> List[ReviewableEntry]:
        from cloud_metrics.models.cim_registry import CimMetricDefinition

        rows = self._session.query(CimMetricDefinition).all()
        out = []
        for row in rows:
            if queue_only and not is_queue_status(row.status):
                continue
            out.append(self._metric_to_reviewable(row))
        return out

    def _metric_entry(self, entity_id: int) -> Optional[ReviewableEntry]:
        from cloud_metrics.models.cim_registry import CimMetricDefinition

        row = self._session.get(CimMetricDefinition, entity_id)
        return self._metric_to_reviewable(row) if row else None

    def _metric_to_reviewable(self, row) -> ReviewableEntry:
        return ReviewableEntry(
            entity_type=ReviewEntityType.METRIC,
            entity_id=row.id,
            status=row.status or "draft",
            review_status=row.review_status or "pending",
            label=row.label,
            namespace_or_key=row.namespace,
            notes=row.notes,
            created_by=row.created_by,
            confidence_score=row.confidence_score,
            details={
                "domain": row.domain,
                "metric_type": row.metric_type,
                "quantity_kind_id": row.quantity_kind_id,
                "canonical_unit_id": row.canonical_unit_id,
            },
        )

    def _list_sources(self, *, queue_only: bool) -> List[ReviewableEntry]:
        from cloud_metrics.models.cim_registry import CimSource

        rows = self._session.query(CimSource).all()
        return [
            self._source_to_reviewable(r)
            for r in rows
            if (not queue_only) or is_queue_status(r.status)
        ]

    def _source_entry(self, entity_id: int) -> Optional[ReviewableEntry]:
        from cloud_metrics.models.cim_registry import CimSource

        row = self._session.get(CimSource, entity_id)
        return self._source_to_reviewable(row) if row else None

    def _source_to_reviewable(self, row) -> ReviewableEntry:
        return ReviewableEntry(
            entity_type=ReviewEntityType.SOURCE,
            entity_id=row.id,
            status=row.status or "candidate",
            review_status=row.review_status or "under_review",
            label=row.name,
            namespace_or_key=row.name,
            notes=row.notes,
            created_by=row.created_by,
            details={"type": row.type, "protocol": row.protocol},
        )

    def _list_assets(self, *, queue_only: bool) -> List[ReviewableEntry]:
        from cloud_metrics.models.cim_registry import CimAsset

        rows = self._session.query(CimAsset).all()
        return [
            self._asset_to_reviewable(r)
            for r in rows
            if (not queue_only) or is_queue_status(r.status)
        ]

    def _asset_entry(self, entity_id: int) -> Optional[ReviewableEntry]:
        from cloud_metrics.models.cim_registry import CimAsset

        row = self._session.get(CimAsset, entity_id)
        return self._asset_to_reviewable(row) if row else None

    def _asset_to_reviewable(self, row) -> ReviewableEntry:
        return ReviewableEntry(
            entity_type=ReviewEntityType.ASSET,
            entity_id=row.id,
            status=row.status or "candidate",
            review_status=row.review_status or "under_review",
            label=row.name,
            namespace_or_key=row.identifier,
            notes=row.notes,
            created_by=row.created_by,
            details={"type": row.type, "parent_id": row.parent_id},
        )

    def _list_units(self, *, queue_only: bool) -> List[ReviewableEntry]:
        from cloud_metrics.models.cim_registry import CimUnit

        rows = self._session.query(CimUnit).all()
        return [
            self._unit_to_reviewable(r)
            for r in rows
            if (not queue_only) or is_queue_status(r.status)
        ]

    def _unit_entry(self, entity_id: int) -> Optional[ReviewableEntry]:
        from cloud_metrics.models.cim_registry import CimUnit

        row = self._session.get(CimUnit, entity_id)
        return self._unit_to_reviewable(row) if row else None

    def _unit_to_reviewable(self, row) -> ReviewableEntry:
        return ReviewableEntry(
            entity_type=ReviewEntityType.UNIT,
            entity_id=row.id,
            status=row.status or "draft",
            review_status=row.review_status or "pending",
            label=row.name,
            namespace_or_key=row.symbol,
            notes=row.notes,
            created_by=row.created_by,
            details={"quantity_kind_id": row.quantity_kind_id},
        )

    def _list_lifecycle_links(self, *, queue_only: bool) -> List[ReviewableEntry]:
        from cloud_metrics.models.cim_registry import CimMetricLifecycleLink

        rows = self._session.query(CimMetricLifecycleLink).all()
        return [
            self._lifecycle_to_reviewable(r)
            for r in rows
            if (not queue_only) or is_queue_status(r.status) or is_queue_status(r.review_status)
        ]

    def _lifecycle_entry(self, entity_id: int) -> Optional[ReviewableEntry]:
        from cloud_metrics.models.cim_registry import CimMetricLifecycleLink

        row = self._session.get(CimMetricLifecycleLink, entity_id)
        return self._lifecycle_to_reviewable(row) if row else None

    def _lifecycle_to_reviewable(self, row) -> ReviewableEntry:
        stage = getattr(row, "lifecycle_stage", None)
        metric = getattr(row, "metric", None)
        return ReviewableEntry(
            entity_type=ReviewEntityType.LIFECYCLE_LINK,
            entity_id=row.id,
            status=row.status or "draft",
            review_status=row.review_status or "pending",
            label=stage.name if stage is not None else None,
            namespace_or_key=metric.namespace if metric is not None else None,
            notes=row.notes,
            created_by=row.created_by,
            details={
                "relevance": row.relevance,
                "lifecycle_stage_id": row.lifecycle_stage_id,
                "metric_id": row.metric_id,
            },
        )


def get_admin_review_service(session: Optional[Session] = None) -> AdminReviewService:
    return AdminReviewService(session=session)


# Aliases matching milestone brief
RegistryReviewService = AdminReviewService
CandidateReviewService = AdminReviewService
get_registry_review_service = get_admin_review_service
get_candidate_review_service = get_admin_review_service
