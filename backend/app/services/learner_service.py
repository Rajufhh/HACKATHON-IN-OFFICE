from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.models.learner import Learner
from app.schemas.learner import LearnerCreate

class LearnerService:
    """
    Encapsulates all learner-related business operations and database queries.
    """
    def __init__(self, db: Session):
        self.db = db

    def create_learner(self, learner_data: LearnerCreate) -> Learner:
        learner = Learner(
            learner_code=learner_data.learner_code,
            name=learner_data.name,
            email=learner_data.email,
            department=learner_data.department
        )
        try:
            self.db.add(learner)
            self.db.commit()
            self.db.refresh(learner)
            return learner
        except IntegrityError:
            self.db.rollback()
            raise ValueError("Learner code or email already exists")

    def get_all_learners(self) -> list[Learner]:
        return self.db.query(Learner).all()

    def get_learner_by_id(self, learner_id: int) -> Learner | None:
        return self.db.query(Learner).filter(Learner.id == learner_id).first()
