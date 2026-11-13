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

class CaseEvent(Base):
    """
    Append-only immutable audit log of case activities.
    Preserves historical transitions, evidence events, and assignments.
    """
    __tablename__ = "case_events"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False, index=True)
    event_type = Column(String(50), nullable=False)  # CASE_OPENED, REVIEWER_ASSIGNED, STATUS_CHANGED, etc.
    description = Column(Text, nullable=False)
    actor_id = Column(Integer, nullable=True)
    actor_role = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    case = relationship("Case", back_populates="events")

