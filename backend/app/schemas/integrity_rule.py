from datetime import datetime
from pydantic import BaseModel, ConfigDict
from typing import Optional

class IntegrityRuleCreate(BaseModel):
    rule_code: str
    rule_name: str
    min_similarity: int
    max_similarity: int
    action: str  # INFORMATION, REVIEW, PRIORITY_REVIEW
    description: Optional[str] = None

class IntegrityRuleResponse(BaseModel):
    id: int
    rule_code: str
    rule_name: str
    min_similarity: int
    max_similarity: int
    action: str
    description: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

