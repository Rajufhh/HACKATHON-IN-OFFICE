from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, Field

class ReviewerConflictCreate(BaseModel):
    reviewer_id: int = Field(gt=0)
    case_id: int = Field(gt=0)
    conflict_type: Literal[
        "PERSONAL",
        "ACADEMIC",
        "FINANCIAL",
        "PROFESSIONAL",
        "OTHER"
    ]
    reason: str = Field(min_length=5, max_length=2000)

class ReviewerConflictResolve(BaseModel):
    decision: Literal["CONFIRMED", "DISMISSED"]
    reviewer_admin_id: int = Field(gt=0)
    review_notes: Optional[str] = None

class ReviewerConflictResponse(BaseModel):
    id: int
    reviewer_id: int
    case_id: int
    conflict_type: str
    reason: str
    status: str
    declared_at: datetime
    reviewed_at: Optional[datetime] = None
    reviewed_by: Optional[int] = None
    review_notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

