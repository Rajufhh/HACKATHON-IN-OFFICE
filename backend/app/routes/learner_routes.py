from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.schemas.learner import LearnerCreate, LearnerResponse
from app.services.learner_service import LearnerService

router = APIRouter(
    prefix="/api/v1/learners",
    tags=["Learners"]
)

@router.post("/", response_model=LearnerResponse, status_code=200)
def create_learner(
    learner_data: LearnerCreate,
    db: Session = Depends(get_db)
):
    service = LearnerService(db)
    try:
        return service.create_learner(learner_data)
    except ValueError as error:
        raise HTTPException(
            status_code=409,
            detail=str(error)
        )

@router.get("/", response_model=list[LearnerResponse])
def get_learners(db: Session = Depends(get_db)):
    service = LearnerService(db)
    return service.get_all_learners()

@router.get("/{learner_id}", response_model=LearnerResponse)
def get_learner(
    learner_id: int,
    db: Session = Depends(get_db)
):
    service = LearnerService(db)
    learner = service.get_learner_by_id(learner_id)
    if not learner:
        raise HTTPException(
            status_code=404,
            detail="Learner not found"
        )
    return learner

