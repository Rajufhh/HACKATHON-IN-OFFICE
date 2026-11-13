from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.schemas.submission import SubmissionCreate, SubmissionResponse
from app.services.submission_service import SubmissionService

router = APIRouter(
    prefix="/api/v1/submissions",
    tags=["Submissions"]
)

@router.post("/", response_model=SubmissionResponse, status_code=200)
def create_submission(
    data: SubmissionCreate,
    db: Session = Depends(get_db)
):
    service = SubmissionService(db)
    try:
        return service.create_submission(data)
    except ValueError as error:
        detail = str(error)
        status_code = 404 if "does not exist" in detail else 409
        raise HTTPException(status_code=status_code, detail=detail)

@router.get("/", response_model=list[SubmissionResponse])
def get_submissions(db: Session = Depends(get_db)):
    service = SubmissionService(db)
    return service.get_all_submissions()

@router.get("/{submission_id}", response_model=SubmissionResponse)
def get_submission(
    submission_id: int,
    db: Session = Depends(get_db)
):
    service = SubmissionService(db)
    submission = service.get_submission_by_id(submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    return submission

@router.delete("/{submission_id}", status_code=204)
def delete_submission(
    submission_id: int,
    db: Session = Depends(get_db)
):
    service = SubmissionService(db)
    try:
        deleted = service.delete_submission(submission_id)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    if not deleted:
        raise HTTPException(status_code=404, detail="Submission not found")
    return Response(status_code=204)

@router.get("/learner/{learner_id}", response_model=list[SubmissionResponse])
def get_learner_submissions(
    learner_id: int,
    db: Session = Depends(get_db)
):
    service = SubmissionService(db)
    return service.get_submissions_by_learner(learner_id)

