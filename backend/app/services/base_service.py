from typing import Type, TypeVar, Generic, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel
from app.database.connection import Base

T = TypeVar("T", bound=Base)

class BaseService(Generic[T]):
    """
    Parent Service implementing common CRUD operations using OOP Inheritance.
    Child classes set the 'model' class attribute.
    """
    model: Type[T] = None

    def __init__(self, db: Session):
        self.db = db

    def create(self, data: BaseModel) -> T:
        """
        Creates a new record from validated Pydantic model data.
        """
        record = self.model(**data.model_dump())
        try:
            self.db.add(record)
            self.db.commit()
            self.db.refresh(record)
            return record
        except IntegrityError as err:
            self.db.rollback()
            raise ValueError(f"Duplicate or invalid record for {self.model.__tablename__}: {err.orig}")

    def get_all(self, skip: int = 0, limit: int = 100) -> List[T]:
        """
        Retrieves all records with pagination support.
        """
        return self.db.query(self.model).offset(skip).limit(limit).all()

    def get_by_id(self, record_id: int) -> Optional[T]:
        """
        Retrieves a record by primary key ID.
        """
        return self.db.query(self.model).filter(self.model.id == record_id).first()

    def delete(self, record_id: int) -> bool:
        """
        Deletes a record by ID.
        """
        record = self.get_by_id(record_id)
        if not record:
            return False
        self.db.delete(record)
        self.db.commit()
        return True

