from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional

class CaseCreate(BaseModel):
    case_code: str = Field(pattern=r"^CASE-\d{4}-\d{6}$")
    flag_id: int = Field(gt=0)
    title: str = Field(min_length=3, max_length=250)
    description: Optional[str] = None

class CaseStatusUpdate(BaseModel):
    status: str = Field(pattern=r"^(ASSIGNED|UNDER_REVIEW|DECISION_PENDING|CLOSED)$")
    reason: Optional[str] = None

class CaseAssignmentCreate(BaseModel):
    reviewer_id: int = Field(gt=0)
    actor_id: Optional[int] = None

class CaseEventResponse(BaseModel):
    id: int
    case_id: int
    event_type: str
    description: str
    actor_id: Optional[int] = None
    actor_role: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class CaseAssignmentResponse(BaseModel):
    id: int
    case_id: int
    reviewer_id: int
    conflict_status: str
    assigned_at: datetime
    unassigned_at: Optional[datetime] = None
    status: str

    model_config = ConfigDict(from_attributes=True)

class CaseResponse(BaseModel):
    id: int
    case_code: str
    learner_id: int
    status: str
    priority: str
    title: str
    description: Optional[str] = None
    opened_at: datetime
    closed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class CaseDetailResponse(CaseResponse):
    events: List[CaseEventResponse] = []
    assignments: List[CaseAssignmentResponse] = []

