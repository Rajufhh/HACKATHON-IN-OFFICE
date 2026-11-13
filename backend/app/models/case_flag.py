from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship
from app.database.connection import Base

class CaseFlag(Base):
    """
    Bridge table connecting cases with one or more similarity flags.
    Enforces that a flag is attached to at most one case (unique flag_id).
    """
    __tablename__ = "case_flags"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False)
    flag_id = Column(Integer, ForeignKey("flags.id"), nullable=False, unique=True)

    # Relationships
    case = relationship("Case", back_populates="flags")
    flag = relationship("Flag")

