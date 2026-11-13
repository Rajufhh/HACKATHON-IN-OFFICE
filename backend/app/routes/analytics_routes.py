from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.schemas.analytics import AnalyticsOverview
from app.services.analytics_service import AnalyticsService


router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/overview", response_model=AnalyticsOverview)
def get_analytics_overview(db: Session = Depends(get_db)) -> AnalyticsOverview:
    return AnalyticsService(db).get_overview()
