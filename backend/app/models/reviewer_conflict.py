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

class ReviewerConflict(Base):
    """
    SQLAlchemy ORM Model representing an explicit conflict-of-interest declaration.
    Enforces independence: pending and confirmed conflicts block case assignment.
    """
    __tablename__ = "reviewer_conflicts"

    id = Column(Integer, primary_key=True, index=True)
    reviewer_id = Column(Integer, ForeignKey("reviewers.id"), nullable=False, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False, index=True)
    conflict_type = Column(String(50), nullable=False)  # PERSONAL, ACADEMIC, FINANCIAL, PROFESSIONAL, OTHER
    reason = Column(Text, nullable=False)
    status = Column(String(30), default="PENDING", nullable=False)  # PENDING, CONFIRMED, DISMISSED, WITHDRAWN
    declared_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    reviewed_at = Column(DateTime, nullable=True)
    reviewed_by = Column(Integer, nullable=True)
    review_notes = Column(Text, nullable=True)

    # Relationships
    reviewer = relationship("Reviewer", back_populates="conflicts")
    case = relationship("Case", back_populates="reviewer_conflicts")

