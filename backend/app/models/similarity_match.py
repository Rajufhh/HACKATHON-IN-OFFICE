from sqlalchemy import Column, Integer, String, ForeignKey, Numeric
from sqlalchemy.orm import relationship
from app.database.connection import Base

class SimilarityMatch(Base):
    """
    SQLAlchemy ORM Model representing an individual matching source
    (e.g., quotes, shared boilerplates/templates, external web, or peer submissions).
    """
    __tablename__ = "similarity_matches"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("similarity_reports.id"), nullable=False, index=True)
    source_type = Column(String(50), nullable=False)  # QUOTATION, TEMPLATE, INTERNET, PEER_SUBMISSION
    source_reference = Column(String(500), nullable=True)
    matched_percentage = Column(Numeric(5, 2), nullable=False)
    description = Column(String(1000), nullable=True)

    # Relationship
    report = relationship("SimilarityReport", back_populates="matches")

