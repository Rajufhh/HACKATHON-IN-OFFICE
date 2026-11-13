from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database.connection import Base


class AppealEvidence(Base):
    """Snapshot of evidence attached to an appeal."""

    __tablename__ = "appeal_evidence"
    __table_args__ = (
        UniqueConstraint("appeal_id", "evidence_id", name="uq_appeal_evidence"),
    )

    id = Column(Integer, primary_key=True, index=True)
    appeal_id = Column(
        Integer,
        ForeignKey("appeals.id"),
        nullable=False,
        index=True,
    )
    evidence_id = Column(
        Integer,
        ForeignKey("evidence_items.id"),
        nullable=False,
        index=True,
    )
    evidence_code_snapshot = Column(String(60), nullable=False)
    evidence_title_snapshot = Column(String(250), nullable=False)
    evidence_type_snapshot = Column(String(50), nullable=False)
    added_by = Column(Integer, nullable=True)
    added_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    appeal = relationship("Appeal", back_populates="evidence_snapshots")
