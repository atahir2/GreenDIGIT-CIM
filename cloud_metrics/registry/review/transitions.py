"""Allowed status transitions for admin review (Milestone 12)."""

from __future__ import annotations

from typing import Dict, FrozenSet, Optional, Set, Tuple

from cloud_metrics.registry.review.types import (
    APPROVED_STATUSES,
    QUEUE_STATUSES,
    ReviewAction,
    TERMINAL_NEGATIVE,
)

# (current_status_normalized, action) -> allowed target status
# review_status is handled separately in the service.

_TRANSITION_TARGETS: Dict[Tuple[str, ReviewAction], str] = {
    # mark under review
    ("candidate", ReviewAction.MARK_UNDER_REVIEW): "under_review",
    ("pending", ReviewAction.MARK_UNDER_REVIEW): "under_review",
    ("draft", ReviewAction.MARK_UNDER_REVIEW): "under_review",
    ("accepted", ReviewAction.MARK_UNDER_REVIEW): "under_review",
    # approve
    ("candidate", ReviewAction.APPROVE): "approved",
    ("under_review", ReviewAction.APPROVE): "approved",
    ("pending", ReviewAction.APPROVE): "approved",
    ("accepted", ReviewAction.APPROVE): "approved",
    ("draft", ReviewAction.APPROVE): "approved",
    # reject
    ("candidate", ReviewAction.REJECT): "rejected",
    ("under_review", ReviewAction.REJECT): "rejected",
    ("pending", ReviewAction.REJECT): "rejected",
    ("accepted", ReviewAction.REJECT): "rejected",
    ("draft", ReviewAction.REJECT): "rejected",
    # request changes keeps/returns to under_review
    ("candidate", ReviewAction.REQUEST_CHANGES): "under_review",
    ("under_review", ReviewAction.REQUEST_CHANGES): "under_review",
    ("accepted", ReviewAction.REQUEST_CHANGES): "under_review",
    # deprecate
    ("approved", ReviewAction.DEPRECATE): "deprecated",
    ("active", ReviewAction.DEPRECATE): "deprecated",
    # merge
    ("candidate", ReviewAction.MERGE): "merged",
    ("under_review", ReviewAction.MERGE): "merged",
    ("pending", ReviewAction.MERGE): "merged",
    ("accepted", ReviewAction.MERGE): "merged",
    # reopen rejected → under_review
    ("rejected", ReviewAction.REOPEN): "under_review",
    ("rejected", ReviewAction.MARK_UNDER_REVIEW): "under_review",
    # edit does not force status change by itself
    ("candidate", ReviewAction.EDIT): "candidate",
    ("under_review", ReviewAction.EDIT): "under_review",
    ("pending", ReviewAction.EDIT): "pending",
    ("accepted", ReviewAction.EDIT): "accepted",
    ("draft", ReviewAction.EDIT): "draft",
    ("rejected", ReviewAction.EDIT): "rejected",
    ("approved", ReviewAction.EDIT): "approved",
    ("active", ReviewAction.EDIT): "active",
    # promote_to_seed requires approved/active (validated in service)
    ("approved", ReviewAction.PROMOTE_TO_SEED): "approved",
    ("active", ReviewAction.PROMOTE_TO_SEED): "approved",
}


def normalize_status(status: Optional[str]) -> str:
    return (status or "").strip().lower()


def is_queue_status(status: Optional[str]) -> bool:
    return normalize_status(status) in QUEUE_STATUSES


def is_approved_status(status: Optional[str]) -> bool:
    return normalize_status(status) in APPROVED_STATUSES


def allowed_target_status(
    current_status: Optional[str], action: ReviewAction
) -> Optional[str]:
    key = (normalize_status(current_status), action)
    return _TRANSITION_TARGETS.get(key)


def assert_transition_allowed(
    current_status: Optional[str],
    action: ReviewAction,
    *,
    allow_reopen: bool = False,
) -> str:
    """Return target status or raise ValueError."""
    current = normalize_status(current_status)
    action = ReviewAction(action)

    # Hard rule: rejected cannot become approved without reopen/edit path
    if action == ReviewAction.APPROVE and current == "rejected":
        raise ValueError(
            "rejected entry cannot be approved directly; reopen or edit first"
        )

    if action == ReviewAction.APPROVE and current in TERMINAL_NEGATIVE - {"merged"}:
        if current == "merged":
            raise ValueError("merged entry cannot be approved; create a new mapping")
        raise ValueError(f"cannot approve from status={current}")

    target = allowed_target_status(current, action)
    if target is None:
        raise ValueError(
            f"transition not allowed: status={current!r} action={action.value!r}"
        )
    return target


def review_status_for_action(action: ReviewAction, target_status: str) -> str:
    if action == ReviewAction.APPROVE:
        return "approved"
    if action == ReviewAction.REJECT:
        return "rejected"
    if action == ReviewAction.DEPRECATE:
        return "approved"  # historically approved, now deprecated
    if action == ReviewAction.MERGE:
        return "approved"  # merge decision accepted
    if action in {
        ReviewAction.MARK_UNDER_REVIEW,
        ReviewAction.REQUEST_CHANGES,
        ReviewAction.REOPEN,
    }:
        return "under_review"
    if action == ReviewAction.PROMOTE_TO_SEED:
        return "approved"
    # edit: leave review_status unchanged by default — caller may override
    return "under_review" if target_status in QUEUE_STATUSES else "approved"
