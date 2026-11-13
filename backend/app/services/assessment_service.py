from app.services.base_service import BaseService
from app.models.assessment import Assessment

class AssessmentService(BaseService[Assessment]):
    """
    Assessment Service inheriting standard CRUD from BaseService.
    Can define domain-specific methods (e.g. filter by status or department).
    """
    model = Assessment

    def get_by_code(self, assessment_code: str) -> Assessment | None:
        return self.db.query(Assessment).filter(Assessment.assessment_code == assessment_code).first()

