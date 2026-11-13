from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from app.database.connection import Base

class Learner(Base):
    """
    SQLAlchemy ORM Model representing the 'learners' table.
    Inherits from DeclarativeBase (Base).
    """
    __tablename__ = "learners"

    id = Column(Integer, primary_key=True, index=True)
    learner_code = Column(String(30), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, nullable=False)
    department = Column(String(100), nullable=False)
    status = Column(String(20), default="ACTIVE")

    # Relationships
    submissions = relationship("Submission", back_populates="learner")
    cases = relationship("Case", back_populates="learner")
    appeals = relationship("Appeal", back_populates="learner")
