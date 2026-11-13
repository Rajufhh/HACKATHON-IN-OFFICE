from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr
from typing import Optional

class ReviewerCreate(BaseModel):
    reviewer_code: str
    full_name: str
    email: EmailStr
    department: str
    specialization: Optional[str] = None
    max_active_cases: int = 10
    status: str = "ACTIVE"

class ReviewerResponse(BaseModel):
    id: int
    reviewer_code: str
    full_name: str
    email: EmailStr
    department: str
    specialization: Optional[str] = None
    max_active_cases: int
    status: str
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

