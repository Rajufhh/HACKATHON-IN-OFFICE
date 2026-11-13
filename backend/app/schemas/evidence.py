from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional


EVIDENCE_TYPES = ["DOCUMENT", "SUBMISSION_VERSION", "EXPLANATION", "SIMILARITY_REPORT", "OTHER"]


class EvidenceCreate(BaseModel):
    case_id: int = Field(..., gt=0)
    evidence_type: str = Field(..., description=f"One of: {EVIDENCE_TYPES}")
    title: str = Field(..., min_length=1, max_length=250)
    description: Optional[str] = None
    source_reference: Optional[str] = Field(None, max_length=500)
    sha256_hash: Optional[str] = Field(None, max_length=64)
    mime_type: Optional[str] = Field(None, max_length=100)
    file_size_bytes: Optional[int] = Field(None, ge=0)
    collected_at: Optional[datetime] = None
    added_by: Optional[int] = None


class EvidenceResponse(BaseModel):
    id: int
    evidence_code: str
    case_id: int
    evidence_type: str
    title: str
    description: Optional[str]
    source_reference: Optional[str]
    sha256_hash: Optional[str]
    mime_type: Optional[str]
    file_size_bytes: Optional[int]
    collected_at: Optional[datetime]
    added_at: datetime
    added_by: Optional[int]

    model_config = {"from_attributes": True}

