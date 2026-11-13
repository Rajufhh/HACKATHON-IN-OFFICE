from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    CheckConstraint
)
from sqlalchemy.orm import relationship
from app.database.connection import Base

class Submission(Base):
    """
    SQLAlchemy ORM Model representing student submissions.
    Demonstrates Foreign Keys and 1:N / N:1 ORM relationships with Learner and Assessment.
    """
    __tablename__ = "submissions"

    id = Column(Integer, primary_key=True, index=True)
    submission_code = Column(String(40), unique=True, nullable=False)
    learner_id = Column(Integer, ForeignKey("learners.id"), nullable=False)
    assessment_id = Column(Integer, ForeignKey("assessments.id"), nullable=False)
    submitted_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    file_reference = Column(String(500), nullable=True)
    content_hash = Column(String(128), nullable=True)
    version_number = Column(Integer, default=1, nullable=False)
    status = Column(String(30), default="SUBMITTED", nullable=False)

    # ORM relationships
    learner = relationship("Learner", back_populates="submissions")
    assessment = relationship("Assessment", back_populates="submissions")
    similarity_reports = relationship("SimilarityReport", back_populates="submission")
    flags = relationship("Flag", back_populates="submission")

    __table_args__ = (
        CheckConstraint("version_number >= 1", name="check_submission_version"),
    )
