from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session
from sqlalchemy.sql import ColumnElement

from app.database.connection import Base
from app.models import (
    Appeal,
    Assessment,
    Case,
    CaseDecision,
    Flag,
    Learner,
    Reviewer,
    Submission,
)
from app.schemas.analytics import (
    AnalyticsOverview,
    DashboardMetrics,
    DistributionItem,
)


class AnalyticsService:
    """Read-only aggregate queries for the dashboard."""

    def __init__(self, db: Session):
        self.db = db

    def count_records(self, model: type[Base]) -> int:
        return self.db.query(model).count()

    def get_distribution(
        self,
        field: ColumnElement[Any],
    ) -> list[DistributionItem]:
        rows = (
            self.db.query(field, func.count())
            .group_by(field)
            .order_by(field.asc())
            .all()
        )
        return [
            DistributionItem(
                label=str(value) if value is not None else "UNKNOWN",
                count=count,
            )
            for value, count in rows
        ]

    def get_overview(self) -> AnalyticsOverview:
        metrics = DashboardMetrics(
            total_learners=self.count_records(Learner),
            total_assessments=self.count_records(Assessment),
            total_submissions=self.count_records(Submission),
            total_flags=self.count_records(Flag),
            total_cases=self.count_records(Case),
            total_reviewers=self.count_records(Reviewer),
            total_decisions=self.count_records(CaseDecision),
            total_appeals=self.count_records(Appeal),
        )
        return AnalyticsOverview(
            metrics=metrics,
            case_status=self.get_distribution(Case.status),
            flag_status=self.get_distribution(Flag.status),
            decision_outcomes=self.get_distribution(CaseDecision.outcome),
            appeal_status=self.get_distribution(Appeal.status),
            appeal_outcomes=self.get_distribution(Appeal.outcome),
        )
