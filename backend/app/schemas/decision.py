from datetime import datetime
from pydantic import BaseModel, Field
from typing import Literal, Optional
from app.schemas.evidence import EvidenceResponse


OUTCOMES = [
    "BREACH_ESTABLISHED",
    "NO_BREACH",
    "INSUFFICIENT_EVIDENCE",
    "REFERRED_FOR_FURTHER_REVIEW",
]


class DecisionCreate(BaseModel):
    case_id: int = Field(..., gt=0)
    reviewer_id: int = Field(..., gt=0)
    outcome: Literal[
        "BREACH_ESTABLISHED",
        "NO_BREACH",
        "INSUFFICIENT_EVIDENCE",
        "REFERRED_FOR_FURTHER_REVIEW",
    ]
    rationale: str = Field(..., min_length=1)
    evidence_ids: list[int] = Field(default_factory=list)


class DecisionEvidenceSnapshotResponse(BaseModel):
    id: int
    decision_id: int
    evidence_id: int
    evidence_code_snapshot: str
    evidence_title_snapshot: str
    evidence_type_snapshot: str

    model_config = {"from_attributes": True}


class DecisionResponse(BaseModel):
    id: int
    decision_code: str
    case_id: int
    reviewer_id: int
    outcome: str
    rationale: str
    decided_at: datetime

    model_config = {"from_attributes": True}


class DecisionDetailResponse(DecisionResponse):
    """Full response including the immutable evidence snapshot."""
    evidence_snapshot: list[DecisionEvidenceSnapshotResponse] = []

