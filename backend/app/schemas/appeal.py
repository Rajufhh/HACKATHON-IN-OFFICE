from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


APPEAL_OUTCOMES = [
    "UPHELD",
    "OVERTURNED",
    "REMANDED",
]


class AppealCreate(BaseModel):
    decision_id: int = Field(..., gt=0)
    learner_id: int = Field(..., gt=0)
    grounds: str = Field(..., min_length=10, max_length=10000)
    evidence_ids: list[int] = Field(default_factory=list)


class AppealEvidenceCreate(BaseModel):
    evidence_id: int = Field(..., gt=0)
    added_by: Optional[int] = None


class AppealAssign(BaseModel):
    reviewer_id: int = Field(..., gt=0)
    actor_id: Optional[int] = None


class AppealResolve(BaseModel):
    reviewer_id: int = Field(..., gt=0)
    outcome: Literal["UPHELD", "OVERTURNED", "REMANDED"]
    rationale: str = Field(..., min_length=10, max_length=10000)


class AppealResponse(BaseModel):
    id: int
    appeal_code: str
    decision_id: int
    learner_id: int
    assigned_reviewer_id: Optional[int]
    grounds: str
    status: str
    outcome: Optional[str]
    outcome_rationale: Optional[str]
    submitted_at: datetime
    assigned_at: Optional[datetime]
    resolved_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class AppealEvidenceResponse(BaseModel):
    id: int
    appeal_id: int
    evidence_id: int
    evidence_code_snapshot: str
    evidence_title_snapshot: str
    evidence_type_snapshot: str
    added_by: Optional[int]
    added_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AppealEventResponse(BaseModel):
    id: int
    appeal_id: int
    event_type: str
    description: str
    actor_id: Optional[int]
    actor_role: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AppealDetailResponse(AppealResponse):
    events: list[AppealEventResponse] = Field(default_factory=list)
    evidence_snapshots: list[AppealEvidenceResponse] = Field(default_factory=list)
