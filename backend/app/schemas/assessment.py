from datetime import datetime
from pydantic import BaseModel, ConfigDict
from typing import Optional

class AssessmentCreate(BaseModel):
    assessment_code: str
    title: str
    description: Optional[str] = None
    assessment_type: str = "ASSIGNMENT"
    max_marks: int = 100
    due_date: Optional[datetime] = None
    status: str = "PUBLISHED"

class AssessmentResponse(BaseModel):
    id: int
    assessment_code: str
    title: str
    description: Optional[str] = None
    assessment_type: str
    max_marks: int
    due_date: Optional[datetime] = None
    status: str
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

