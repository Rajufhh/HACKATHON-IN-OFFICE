from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.schemas.assessment import AssessmentCreate, AssessmentResponse
from app.services.assessment_service import AssessmentService

router = APIRouter(
    prefix="/api/v1/assessments",
    tags=["Assessments"]
)

@router.post("/", response_model=AssessmentResponse, status_code=200)
def create_assessment(
    assessment_data: AssessmentCreate,
    db: Session = Depends(get_db)
):
    service = AssessmentService(db)
    try:
        return service.create(assessment_data)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error))

@router.get("/", response_model=list[AssessmentResponse])
def get_assessments(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    service = AssessmentService(db)
    return service.get_all(skip=skip, limit=limit)

@router.get("/{assessment_id}", response_model=AssessmentResponse)
def get_assessment(
    assessment_id: int,
    db: Session = Depends(get_db)
):
    service = AssessmentService(db)
    assessment = service.get_by_id(assessment_id)
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return assessment

