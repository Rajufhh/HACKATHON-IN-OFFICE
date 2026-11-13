from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, BigInteger
from sqlalchemy.orm import relationship
from app.database.connection import Base


class EvidenceItem(Base):
    """
    OOP Concept — Encapsulation:
    All evidence fields (provenance, hash, size) are bundled together inside
    this single class.  No caller needs to know the internal DB columns.
    """
    __tablename__ = "evidence_items"

    id                 = Column(Integer, primary_key=True, index=True)
    evidence_code      = Column(String(60), unique=True, nullable=False)
    case_id            = Column(Integer, ForeignKey("cases.id"), nullable=False, index=True)

    # What kind of evidence is this?
    evidence_type      = Column(String(50), nullable=False)
    # Allowed values: DOCUMENT, SUBMISSION_VERSION, EXPLANATION, SIMILARITY_REPORT, OTHER

    title              = Column(String(250), nullable=False)
    description        = Column(Text, nullable=True)

    # Where did it come from?
    source_reference   = Column(String(500), nullable=True)

    # Integrity check — did the content change after collection?
    sha256_hash        = Column(String(64), nullable=True)
    mime_type          = Column(String(100), nullable=True)
    file_size_bytes    = Column(BigInteger, nullable=True)

    collected_at       = Column(DateTime, nullable=True)
    added_at           = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    added_by           = Column(Integer, nullable=True)   # reviewer / system user id

    # Relationships
    case           = relationship("Case", back_populates="evidence_items")
    decision_links = relationship("DecisionEvidence", back_populates="evidence")

