from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.schemas.case import (
    CaseCreate,
    CaseResponse,
    CaseDetailResponse,
    CaseStatusUpdate,
    CaseAssignmentCreate,
    CaseEventResponse
)
from app.services.case_service import CaseService
from app.services.case_event_service import CaseEventService

router = APIRouter(
    prefix="/cases",
    tags=["Case Management"]
)

@router.post("/", response_model=CaseResponse, status_code=201)
def create_case(
    payload: CaseCreate,
    db: Session = Depends(get_db)
):
    service = CaseService(db)
    try:
        return service.create_case(**payload.model_dump())
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc)
        )

@router.get("/", response_model=list[CaseResponse])
def get_cases(
    status: str | None = None,
    db: Session = Depends(get_db)
):
    service = CaseService(db)
    return service.get_all_cases(status=status)

@router.get("/{case_id}", response_model=CaseDetailResponse)
def get_case(
    case_id: int,
    db: Session = Depends(get_db)
):
    service = CaseService(db)
    case = service.get_case_by_id(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case

@router.patch("/{case_id}/status", response_model=CaseResponse)
def update_case_status(
    case_id: int,
    payload: CaseStatusUpdate,
    db: Session = Depends(get_db)
):
    service = CaseService(db)
    try:
        return service.update_case_status(
            case_id=case_id,
            new_status=payload.status,
            reason=payload.reason
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@router.post("/{case_id}/assign", response_model=CaseResponse)
def assign_reviewer(
    case_id: int,
    payload: CaseAssignmentCreate,
    db: Session = Depends(get_db)
):
    service = CaseService(db)
    try:
        return service.assign_reviewer(
            case_id=case_id,
            reviewer_id=payload.reviewer_id,
            actor_id=payload.actor_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@router.get("/{case_id}/events", response_model=list[CaseEventResponse])
def get_case_events(
    case_id: int,
    db: Session = Depends(get_db)
):
    event_service = CaseEventService(db)
    return event_service.get_case_events(case_id)

