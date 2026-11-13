from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database.connection import Base


class CaseDecision(Base):
    """
    OOP Concept — Immutability via design:
    Once a decision is recorded it is NEVER updated or deleted.
    If a reviewer changes their mind, a new CaseDecision is created with
    its own evidence snapshot.  The old decision is preserved for audit.
    """
    __tablename__ = "case_decisions"

    id              = Column(Integer, primary_key=True, index=True)
    decision_code   = Column(String(60), unique=True, nullable=False)
    case_id         = Column(Integer, ForeignKey("cases.id"), nullable=False, index=True)
    reviewer_id     = Column(Integer, ForeignKey("reviewers.id"), nullable=False, index=True)

    # What was the outcome?
    outcome = Column(String(50), nullable=False)
    # Allowed values:
    #   BREACH_ESTABLISHED        — evidence supports a breach finding
    #   NO_BREACH                 — evidence does not support a breach
    #   INSUFFICIENT_EVIDENCE     — not enough evidence to decide
    #   REFERRED_FOR_FURTHER_REVIEW — needs escalation

    # Must be non-empty — a decision without reasoning is not valid
    rationale  = Column(Text, nullable=False)
    decided_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    case              = relationship("Case", back_populates="decisions")
    reviewer          = relationship("Reviewer", back_populates="decisions")
    evidence_snapshot = relationship("DecisionEvidence", back_populates="decision")
    appeals           = relationship("Appeal", back_populates="decision")

