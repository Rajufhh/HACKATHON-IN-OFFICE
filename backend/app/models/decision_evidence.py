from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.database.connection import Base


class DecisionEvidence(Base):
    """
    OOP Concept — Snapshot / Value Object pattern:
    The *_snapshot columns copy the evidence title, code and type at the
    exact moment the decision is recorded.

    Why?  Because evidence metadata can be corrected later.  The snapshot
    preserves what the reviewer actually saw when they made the decision.

    Adding new evidence after a decision NEVER changes existing snapshot rows.
    """
    __tablename__ = "decision_evidence"

    id                      = Column(Integer, primary_key=True, index=True)
    decision_id             = Column(Integer, ForeignKey("case_decisions.id"), nullable=False, index=True)
    evidence_id             = Column(Integer, ForeignKey("evidence_items.id"), nullable=False)

    # Immutable snapshot — copied at decision time, never updated
    evidence_code_snapshot  = Column(String(60),  nullable=False)
    evidence_title_snapshot = Column(String(250), nullable=False)
    evidence_type_snapshot  = Column(String(50),  nullable=False)

    # Relationships
    decision = relationship("CaseDecision", back_populates="evidence_snapshot")
    evidence = relationship("EvidenceItem",  back_populates="decision_links")

