from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
)
from sqlalchemy.orm import relationship, synonym
from app.database.connection import Base

class CaseAssignment(Base):
    """
    Records reviewer assignment to a case, along with conflict-of-interest status.
    Reviewers with confirmed conflicts cannot be assigned.
    """
    __tablename__ = "case_assignments"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False)
    reviewer_id = Column(Integer, ForeignKey("reviewers.id"), nullable=False)
    conflict_status = Column(String(30), default="NOT_CHECKED", nullable=False)  # NOT_CHECKED, CLEARED, CONFLICT_DETECTED
    assigned_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    unassigned_at = Column(DateTime, nullable=True)
    status = Column(String(30), default="ACTIVE", nullable=False)  # ACTIVE, REPLACED, COMPLETED

    # Synonym allowing either .status or .assignment_status
    assignment_status = synonym("status")

    # Relationships
    case = relationship("Case", back_populates="assignments")
    reviewer = relationship("Reviewer", back_populates="assignments")
