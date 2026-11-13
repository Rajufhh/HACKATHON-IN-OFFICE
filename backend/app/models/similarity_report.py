from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Numeric,
    CheckConstraint,
)
from sqlalchemy.orm import relationship
from app.database.connection import Base

class SimilarityReport(Base):
    """
    SQLAlchemy ORM Model representing an overall similarity analysis on a submission.
    Preserves audit history: a submission can have multiple analysis reports.
    """
    __tablename__ = "similarity_reports"

    id = Column(Integer, primary_key=True, index=True)
    report_code = Column(String(60), unique=True, nullable=False)
    submission_id = Column(Integer, ForeignKey("submissions.id"), nullable=False, index=True)
    overall_score = Column(Numeric(5, 2), nullable=False)
    quotation_percentage = Column(Numeric(5, 2), default=0.0, nullable=False)
    template_percentage = Column(Numeric(5, 2), default=0.0, nullable=False)
    internet_percentage = Column(Numeric(5, 2), default=0.0, nullable=False)
    analyzed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    status = Column(String(30), default="COMPLETED", nullable=False)

    # Relationships (historical records are preserved, no cascade delete)
    submission = relationship("Submission", back_populates="similarity_reports")
    matches = relationship("SimilarityMatch", back_populates="report")
    flags = relationship("Flag", back_populates="report")

    __table_args__ = (
        CheckConstraint("overall_score >= 0.0 AND overall_score <= 100.0", name="check_overall_score_range"),
    )

