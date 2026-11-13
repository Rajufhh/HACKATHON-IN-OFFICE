from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.schemas.similarity import (
    SimilarityReportResponse,
    FlagResponse,
    AnalysisExecutionResponse
)
from app.services.similarity_service import SimilarityService

router = APIRouter(
    prefix="/api/v1/similarity",
    tags=["Similarity Engine"]
)

@router.post("/analyze/{submission_id}", response_model=AnalysisExecutionResponse)
def analyze_submission(
    submission_id: int,
    db: Session = Depends(get_db)
):
    service = SimilarityService(db)
    try:
        result = service.analyze_submission(submission_id)
        return result
    except ValueError as err:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(err))

@router.get("/reports/submission/{submission_id}", response_model=list[SimilarityReportResponse])
def get_submission_reports(
    submission_id: int,
    db: Session = Depends(get_db)
):
    service = SimilarityService(db)
    return service.get_reports_by_submission(submission_id)

@router.get("/flags", response_model=list[FlagResponse])
def get_flags(
    status: str | None = None,
    db: Session = Depends(get_db)
):
    service = SimilarityService(db)
    return service.get_all_flags(status=status)

@router.get("/flags/{flag_id}", response_model=FlagResponse)
def get_flag(
    flag_id: int,
    db: Session = Depends(get_db)
):
    service = SimilarityService(db)
    flag = service.get_flag_by_id(flag_id)
    if not flag:
        raise HTTPException(status_code=404, detail="Flag not found")
    return flag

