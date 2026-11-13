from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship

from app.database.connection import Base


class Appeal(Base):
    """
    Represents a learner's appeal against an existing case decision.

    An appeal is a separate record and never overwrites the original
    CaseDecision.
    """

    __tablename__ = "appeals"

    id = Column(Integer, primary_key=True, index=True)
    appeal_code = Column(String(60), unique=True, nullable=False, index=True)
    decision_id = Column(
        Integer,
        ForeignKey("case_decisions.id"),
        nullable=False,
        unique=True,
        index=True,
    )
    learner_id = Column(
        Integer,
        ForeignKey("learners.id"),
        nullable=False,
        index=True,
    )
    assigned_reviewer_id = Column(
        Integer,
        ForeignKey("reviewers.id"),
        nullable=True,
        index=True,
    )
    grounds = Column(Text, nullable=False)
    status = Column(String(30), default="SUBMITTED", nullable=False)
    outcome = Column(String(30), nullable=True)
    outcome_rationale = Column(Text, nullable=True)
    submitted_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    assigned_at = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)

    decision = relationship("CaseDecision", back_populates="appeals")
    learner = relationship("Learner", back_populates="appeals")
    assigned_reviewer = relationship(
        "Reviewer",
        back_populates="assigned_appeals",
        foreign_keys=[assigned_reviewer_id],
    )
    events = relationship(
        "AppealEvent",
        back_populates="appeal",
        order_by="AppealEvent.created_at",
    )
    evidence_snapshots = relationship(
        "AppealEvidence",
        back_populates="appeal",
        order_by="AppealEvidence.added_at",
    )
