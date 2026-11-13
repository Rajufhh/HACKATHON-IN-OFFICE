from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Text
)
from sqlalchemy.orm import relationship
from app.database.connection import Base

class Flag(Base):
    """
    SQLAlchemy ORM Model representing an integrity review flag.
    A flag is a procedural signal that human due process review is recommended.
    It does NOT declare a learner guilty of misconduct.
    """
    __tablename__ = "flags"

    id = Column(Integer, primary_key=True, index=True)
    flag_code = Column(String(60), unique=True, nullable=False)
    submission_id = Column(Integer, ForeignKey("submissions.id"), nullable=False, index=True)
    report_id = Column(Integer, ForeignKey("similarity_reports.id"), nullable=False, index=True)
    integrity_rule_id = Column(Integer, ForeignKey("integrity_rules.id"), nullable=False, index=True)
    flag_type = Column(String(50), nullable=False)  # INFORMATION, REVIEW, PRIORITY_REVIEW
    status = Column(String(30), default="OPEN", nullable=False)  # OPEN, ASSIGNED, UNDER_REVIEW, RESOLVED, DISMISSED
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # ORM relationships
    submission = relationship("Submission", back_populates="flags")
    report = relationship("SimilarityReport", back_populates="flags")
    integrity_rule = relationship("IntegrityRule", back_populates="flags")

