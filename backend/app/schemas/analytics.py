from pydantic import BaseModel


class DashboardMetrics(BaseModel):
    total_learners: int
    total_assessments: int
    total_submissions: int
    total_flags: int
    total_cases: int
    total_reviewers: int
    total_decisions: int
    total_appeals: int


class DistributionItem(BaseModel):
    label: str
    count: int


class AnalyticsOverview(BaseModel):
    metrics: DashboardMetrics
    case_status: list[DistributionItem]
    flag_status: list[DistributionItem]
    decision_outcomes: list[DistributionItem]
    appeal_status: list[DistributionItem]
    appeal_outcomes: list[DistributionItem]
