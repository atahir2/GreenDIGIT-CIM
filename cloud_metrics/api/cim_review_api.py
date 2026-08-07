# cloud_metrics/api/cim_review_api.py
"""CIM Admin Review API (Milestone 12) — additive; does not replace legacy registry_api."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from cloud_metrics.registry.review import ReviewAction, ReviewEntityType, get_admin_review_service
from cloud_metrics.utils.config import SessionLocal

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class ReviewActionBody(BaseModel):
    reviewer: str
    notes: Optional[str] = None
    edits: Optional[Dict[str, Any]] = None
    merge_target_namespace: Optional[str] = None
    allow_exact_match: bool = False


class ReviewableOut(BaseModel):
    entity_type: str
    entity_id: int
    status: str
    review_status: str
    label: Optional[str] = None
    namespace_or_key: Optional[str] = None
    origin: Optional[str] = None
    relation_type: Optional[str] = None
    justification: Optional[str] = None
    notes: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)


@router.get("/candidates", response_model=List[ReviewableOut])
def list_candidates(
    entity_type: Optional[str] = None,
    db=Depends(get_db),
):
    svc = get_admin_review_service(db)
    types = [entity_type] if entity_type else None
    try:
        entries = svc.list_pending(entity_types=types)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return [ReviewableOut(**e.to_dict()) for e in entries]


@router.get("/candidates/{entity_type}/{entity_id}", response_model=ReviewableOut)
def get_candidate(entity_type: str, entity_id: int, db=Depends(get_db)):
    svc = get_admin_review_service(db)
    try:
        entry = svc.get_entry(entity_type, entity_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if entry is None:
        raise HTTPException(status_code=404, detail="not found")
    return ReviewableOut(**entry.to_dict())


def _apply(entity_type: str, entity_id: int, action: ReviewAction, body: ReviewActionBody, db):
    svc = get_admin_review_service(db)
    try:
        decision = svc.apply(
            entity_type,
            entity_id,
            action,
            reviewer=body.reviewer,
            notes=body.notes,
            edits=body.edits,
            merge_target_namespace=body.merge_target_namespace,
            allow_exact_match=body.allow_exact_match,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not decision.ok:
        raise HTTPException(status_code=409, detail=decision.to_dict())
    return decision.to_dict()


@router.post("/candidates/{entity_type}/{entity_id}/approve")
def approve_candidate(entity_type: str, entity_id: int, body: ReviewActionBody, db=Depends(get_db)):
    return _apply(entity_type, entity_id, ReviewAction.APPROVE, body, db)


@router.post("/candidates/{entity_type}/{entity_id}/reject")
def reject_candidate(entity_type: str, entity_id: int, body: ReviewActionBody, db=Depends(get_db)):
    return _apply(entity_type, entity_id, ReviewAction.REJECT, body, db)


@router.post("/candidates/{entity_type}/{entity_id}/merge")
def merge_candidate(entity_type: str, entity_id: int, body: ReviewActionBody, db=Depends(get_db)):
    if not body.merge_target_namespace:
        raise HTTPException(status_code=400, detail="merge_target_namespace required")
    return _apply(entity_type, entity_id, ReviewAction.MERGE, body, db)


@router.post("/candidates/{entity_type}/{entity_id}/promote")
def promote_candidate(entity_type: str, entity_id: int, body: ReviewActionBody, db=Depends(get_db)):
    return _apply(entity_type, entity_id, ReviewAction.PROMOTE_TO_SEED, body, db)


@router.post("/candidates/{entity_type}/{entity_id}/deprecate")
def deprecate_candidate(entity_type: str, entity_id: int, body: ReviewActionBody, db=Depends(get_db)):
    return _apply(entity_type, entity_id, ReviewAction.DEPRECATE, body, db)


# Silence unused import warnings for enum re-export clarity
_ = ReviewEntityType
