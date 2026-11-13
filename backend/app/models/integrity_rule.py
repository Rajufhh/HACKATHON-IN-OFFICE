from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.orm import relationship
from app.database.connection import Base

class IntegrityRule(Base):
    """
    SQLAlchemy ORM Model representing the 'integrity_rules' table.
    Defines configurable similarity score thresholds and triggered actions.
    Inherits from DeclarativeBase (Base).
    """
    __tablename__ = "integrity_rules"

    id = Column(Integer, primary_key=True, index=True)
    rule_code = Column(String(30), unique=True, nullable=False)
    rule_name = Column(String(150), nullable=False)
    min_similarity = Column(Integer, nullable=False)
    max_similarity = Column(Integer, nullable=False)
    action = Column(String(50), nullable=False)  # INFORMATION, REVIEW, PRIORITY_REVIEW
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    flags = relationship("Flag", back_populates="integrity_rule")
