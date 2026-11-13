from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.schemas.reviewer import ReviewerCreate, ReviewerResponse
from app.services.reviewer_service import ReviewerService

router = APIRouter(
    prefix="/api/v1/reviewers",
    tags=["Reviewers"]
)

@router.post("/", response_model=ReviewerResponse, status_code=200)
def create_reviewer(
    reviewer_data: ReviewerCreate,
    db: Session = Depends(get_db)
):
    service = ReviewerService(db)
    try:
        return service.create(reviewer_data)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error))

@router.get("/", response_model=list[ReviewerResponse])
def get_reviewers(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    service = ReviewerService(db)
    return service.get_all(skip=skip, limit=limit)

@router.get("/{reviewer_id}", response_model=ReviewerResponse)
def get_reviewer(
    reviewer_id: int,
    db: Session = Depends(get_db)
):
    service = ReviewerService(db)
    reviewer = service.get_by_id(reviewer_id)
    if not reviewer:
        raise HTTPException(status_code=404, detail="Reviewer not found")
    return reviewer

