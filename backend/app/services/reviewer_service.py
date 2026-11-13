from app.services.base_service import BaseService
from app.models.reviewer import Reviewer

class ReviewerService(BaseService[Reviewer]):
    """
    Reviewer Service inheriting standard CRUD from BaseService.
    Can define domain-specific methods (e.g. available reviewers, specialization search).
    """
    model = Reviewer

    def get_by_code(self, reviewer_code: str) -> Reviewer | None:
        return self.db.query(Reviewer).filter(Reviewer.reviewer_code == reviewer_code).first()

    def get_active_reviewers(self) -> list[Reviewer]:
        return self.db.query(Reviewer).filter(Reviewer.status == "ACTIVE").all()

