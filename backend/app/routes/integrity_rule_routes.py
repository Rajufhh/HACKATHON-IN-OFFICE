from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.schemas.integrity_rule import IntegrityRuleCreate, IntegrityRuleResponse
from app.services.integrity_rule_service import IntegrityRuleService

router = APIRouter(
    prefix="/api/v1/integrity-rules",
    tags=["Integrity Rules"]
)

@router.post("/", response_model=IntegrityRuleResponse, status_code=200)
def create_integrity_rule(
    rule_data: IntegrityRuleCreate,
    db: Session = Depends(get_db)
):
    service = IntegrityRuleService(db)
    try:
        return service.create(rule_data)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error))

@router.get("/", response_model=list[IntegrityRuleResponse])
def get_integrity_rules(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    service = IntegrityRuleService(db)
    return service.get_all(skip=skip, limit=limit)

@router.get("/{rule_id}", response_model=IntegrityRuleResponse)
def get_integrity_rule(
    rule_id: int,
    db: Session = Depends(get_db)
):
    service = IntegrityRuleService(db)
    rule = service.get_by_id(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Integrity rule not found")
    return rule

@router.get("/evaluate/{score}")
def evaluate_similarity_score(
    score: float,
    db: Session = Depends(get_db)
):
    service = IntegrityRuleService(db)
    action = service.evaluate_similarity(score)
    return {
        "similarity_score": score,
        "recommended_action": action,
        "due_process_note": "A similarity flag requires review and does not establish guilt."
    }

