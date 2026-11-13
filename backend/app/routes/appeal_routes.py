from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.schemas.appeal import (
    AppealAssign,
    AppealCreate,
    AppealDetailResponse,
    AppealEvidenceCreate,
    AppealEvidenceResponse,
    AppealEventResponse,
    AppealResponse,
    AppealResolve,
)
from app.services.appeal_service import AppealService


router = APIRouter(prefix="/appeals", tags=["Appeals"])


@router.post("/", response_model=AppealResponse, status_code=201)
def submit_appeal(
    payload: AppealCreate,
    db: Session = Depends(get_db),
):
    service = AppealService(db)
    try:
        appeal = service.submit_appeal(
            decision_id=payload.decision_id,
            learner_id=payload.learner_id,
            grounds=payload.grounds,
            evidence_ids=payload.evidence_ids,
        )
        db.commit()
        db.refresh(appeal)
        return appeal
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/", response_model=list[AppealResponse])
def list_appeals(
    status: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    return AppealService(db).list_appeals(status)


@router.get("/{appeal_id}", response_model=AppealDetailResponse)
def get_appeal(
    appeal_id: int,
    db: Session = Depends(get_db),
):
    appeal = AppealService(db).get_appeal(appeal_id)
    if not appeal:
        raise HTTPException(status_code=404, detail="Appeal not found.")
    return appeal


@router.post(
    "/{appeal_id}/evidence",
    response_model=AppealEvidenceResponse,
    status_code=201,
)
def add_appeal_evidence(
    appeal_id: int,
    payload: AppealEvidenceCreate,
    db: Session = Depends(get_db),
):
    service = AppealService(db)
    try:
        snapshot = service.add_evidence(
            appeal_id=appeal_id,
            evidence_id=payload.evidence_id,
            added_by=payload.added_by,
        )
        db.commit()
        db.refresh(snapshot)
        return snapshot
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/{appeal_id}/assign", response_model=AppealResponse)
def assign_appeal_reviewer(
    appeal_id: int,
    payload: AppealAssign,
    db: Session = Depends(get_db),
):
    service = AppealService(db)
    try:
        appeal = service.assign_reviewer(
            appeal_id=appeal_id,
            reviewer_id=payload.reviewer_id,
            actor_id=payload.actor_id,
        )
        db.commit()
        db.refresh(appeal)
        return appeal
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/{appeal_id}/resolve", response_model=AppealResponse)
def resolve_appeal(
    appeal_id: int,
    payload: AppealResolve,
    db: Session = Depends(get_db),
):
    service = AppealService(db)
    try:
        appeal = service.resolve_appeal(
            appeal_id=appeal_id,
            reviewer_id=payload.reviewer_id,
            outcome=payload.outcome,
            rationale=payload.rationale,
        )
        db.commit()
        db.refresh(appeal)
        return appeal
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/{appeal_id}/withdraw", response_model=AppealResponse)
def withdraw_appeal(
    appeal_id: int,
    learner_id: int,
    db: Session = Depends(get_db),
):
    service = AppealService(db)
    try:
        appeal = service.withdraw_appeal(
            appeal_id=appeal_id,
            learner_id=learner_id,
        )
        db.commit()
        db.refresh(appeal)
        return appeal
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/{appeal_id}/events", response_model=list[AppealEventResponse])
def get_appeal_events(
    appeal_id: int,
    db: Session = Depends(get_db),
):
    service = AppealService(db)
    try:
        return service.get_events(appeal_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
