from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Text,
)
from sqlalchemy.orm import relationship
from app.database.connection import Base

class Case(Base):
    """
    SQLAlchemy ORM Model representing an academic integrity investigation case.
    A case enforces due process: an opened case does NOT imply misconduct.
    """
    __tablename__ = "cases"

    id = Column(Integer, primary_key=True, index=True)
    case_code = Column(String(60), unique=True, nullable=False)
    learner_id = Column(Integer, ForeignKey("learners.id"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(30), default="OPEN", nullable=False)  # OPEN, ASSIGNED, UNDER_REVIEW, DECISION_PENDING, CLOSED, APPEALED
    priority = Column(String(20), default="NORMAL", nullable=False)  # LOW, NORMAL, HIGH, URGENT
    opened_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    closed_at = Column(DateTime, nullable=True)

    # Relationships
    learner             = relationship("Learner", back_populates="cases")
    flags               = relationship("CaseFlag", back_populates="case")
    assignments         = relationship("CaseAssignment", back_populates="case")
    events              = relationship("CaseEvent", back_populates="case")
    reviewer_conflicts  = relationship("ReviewerConflict", back_populates="case")
    evidence_items      = relationship("EvidenceItem", back_populates="case")
    decisions           = relationship("CaseDecision", back_populates="case")
