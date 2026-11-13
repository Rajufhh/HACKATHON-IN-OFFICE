from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from app.database.connection import Base

class Reviewer(Base):
    """
    SQLAlchemy ORM Model representing the 'reviewers' table.
    Inherits from DeclarativeBase (Base).
    """
    __tablename__ = "reviewers"

    id = Column(Integer, primary_key=True, index=True)
    reviewer_code = Column(String(30), unique=True, nullable=False)
    full_name = Column(String(150), nullable=False)
    email = Column(String(150), unique=True, nullable=False)
    department = Column(String(100), nullable=False)
    specialization = Column(String(100), nullable=True)
    max_active_cases = Column(Integer, default=10)
    status = Column(String(20), default="ACTIVE")  # ACTIVE, ON_LEAVE, INACTIVE
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    assignments = relationship("CaseAssignment", back_populates="reviewer")
    conflicts   = relationship("ReviewerConflict", back_populates="reviewer")
    decisions   = relationship("CaseDecision", back_populates="reviewer")
    assigned_appeals = relationship(
        "Appeal",
        back_populates="assigned_reviewer",
        foreign_keys="Appeal.assigned_reviewer_id",
    )
