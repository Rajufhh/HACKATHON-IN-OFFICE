from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.schemas.decision import DecisionCreate, DecisionResponse, DecisionDetailResponse
from app.services.case_decision_service import CaseDecisionService

router = APIRouter(prefix="/decisions", tags=["Decisions"])


@router.post("/", response_model=DecisionResponse, status_code=201)
def record_decision(payload: DecisionCreate, db: Session = Depends(get_db)):
    """
    Record a human decision on a case.

    Rules enforced:
    - Case must be DECISION_PENDING.
    - Reviewer must have ACTIVE + CLEARED assignment.
    - Rationale must be non-empty.
    - All evidence_ids must belong to the same case.
    """
    svc = CaseDecisionService(db)
    try:
        decision = svc.record_decision(
            case_id=payload.case_id,
            reviewer_id=payload.reviewer_id,
            outcome=payload.outcome,
            rationale=payload.rationale,
            evidence_ids=payload.evidence_ids,
        )
        db.commit()
        db.refresh(decision)
        return decision
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc))


@router.get("/case/{case_id}", response_model=list[DecisionResponse])
def list_case_decisions(case_id: int, db: Session = Depends(get_db)):
    """Return all decisions recorded for a case."""
    svc = CaseDecisionService(db)
    return svc.get_case_decisions(case_id)


@router.get("/{decision_id}", response_model=DecisionDetailResponse)
def get_decision(decision_id: int, db: Session = Depends(get_db)):
    """
    Return a single decision including its immutable evidence snapshot.

    The snapshot shows exactly which evidence was considered at decision time —
    even if new evidence was added to the case afterward.
    """
    svc = CaseDecisionService(db)
    decision = svc.get_decision_by_id(decision_id)
    if not decision:
        raise HTTPException(status_code=404, detail=f"Decision {decision_id} not found.")
    return decision

