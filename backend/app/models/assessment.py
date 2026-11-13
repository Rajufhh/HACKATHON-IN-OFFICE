from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.orm import relationship
from app.database.connection import Base

class Assessment(Base):
    """
    SQLAlchemy ORM Model representing the 'assessments' table.
    Inherits from DeclarativeBase (Base).
    """
    __tablename__ = "assessments"

    id = Column(Integer, primary_key=True, index=True)
    assessment_code = Column(String(30), unique=True, nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    assessment_type = Column(String(30), nullable=False)  # ASSIGNMENT, PROJECT, EXAM, QUIZ
    max_marks = Column(Integer, nullable=False, default=100)
    due_date = Column(DateTime, nullable=True)
    status = Column(String(20), default="PUBLISHED")  # DRAFT, PUBLISHED, ARCHIVED
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # One-to-Many relationship with submissions
    submissions = relationship("Submission", back_populates="assessment")
