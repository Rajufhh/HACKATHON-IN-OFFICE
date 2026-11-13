import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "mysql+pymysql://root@localhost:3306/academic_integrity"
)

# Base class for all database models
class Base(DeclarativeBase):
    pass

# Database engine
engine = create_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True
)

# Database session
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False
)

# Database connection dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

