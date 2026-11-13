from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.schemas.reviewer_conflict import (
    ReviewerConflictCreate,
    ReviewerConflictResolve,
    ReviewerConflictResponse
)
from app.services.reviewer_conflict_service import ReviewerConflictService

router = APIRouter(
    prefix="/conflicts",
    tags=["Reviewer Conflicts"]
)

@router.post("/", response_model=ReviewerConflictResponse, status_code=201)
def declare_conflict(
    payload: ReviewerConflictCreate,
    db: Session = Depends(get_db)
):
    service = ReviewerConflictService(db)
    try:
        conflict = service.declare_conflict(
            reviewer_id=payload.reviewer_id,
            case_id=payload.case_id,
            conflict_type=payload.conflict_type,
            reason=payload.reason
        )
        db.commit()
        db.refresh(conflict)
        return conflict
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@router.patch("/{conflict_id}/resolve", response_model=ReviewerConflictResponse)
def resolve_conflict(
    conflict_id: int,
    payload: ReviewerConflictResolve,
    db: Session = Depends(get_db)
):
    service = ReviewerConflictService(db)
    try:
        conflict = service.resolve_conflict(
            conflict_id=conflict_id,
            decision=payload.decision,
            reviewer_admin_id=payload.reviewer_admin_id,
            review_notes=payload.review_notes
        )
        db.commit()
        db.refresh(conflict)
        return conflict
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@router.get("/case/{case_id}", response_model=list[ReviewerConflictResponse])
def get_case_conflicts(
    case_id: int,
    db: Session = Depends(get_db)
):
    service = ReviewerConflictService(db)
    return service.get_conflicts_for_case(case_id)

@router.get("/reviewer/{reviewer_id}", response_model=list[ReviewerConflictResponse])
def get_reviewer_conflicts(
    reviewer_id: int,
    db: Session = Depends(get_db)
):
    service = ReviewerConflictService(db)
    return service.get_conflicts_for_reviewer(reviewer_id)

