from datetime import datetime
from pydantic import BaseModel, ConfigDict
from typing import List, Optional

class SimilarityMatchResponse(BaseModel):
    id: int
    source_type: str
    source_reference: Optional[str] = None
    matched_percentage: float
    description: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class SimilarityReportResponse(BaseModel):
    id: int
    report_code: str
    submission_id: int
    overall_score: float
    quotation_percentage: float
    template_percentage: float
    internet_percentage: float
    analyzed_at: datetime
    status: str
    matches: List[SimilarityMatchResponse] = []

    model_config = ConfigDict(from_attributes=True)

class FlagResponse(BaseModel):
    id: int
    flag_code: str
    submission_id: int
    report_id: int
    integrity_rule_id: int
    flag_type: str
    status: str
    reason: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class AnalysisExecutionResponse(BaseModel):
    report: SimilarityReportResponse
    rule_action: str
    flag_created: bool
    flag: Optional[FlagResponse] = None
    due_process_notice: str

