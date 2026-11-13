from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

class SubmissionCreate(BaseModel):
    submission_code: str = Field(pattern=r"^SUB-\d{4}-\d{6}$")
    learner_id: int = Field(gt=0)
    assessment_id: int = Field(gt=0)
    file_reference: str | None = None
    content_hash: str | None = None
    version_number: int = Field(default=1, ge=1)

class SubmissionResponse(BaseModel):
    id: int
    submission_code: str
    learner_id: int
    assessment_id: int
    submitted_at: datetime
    file_reference: str | None
    content_hash: str | None
    version_number: int
    status: str

    model_config = ConfigDict(from_attributes=True)

