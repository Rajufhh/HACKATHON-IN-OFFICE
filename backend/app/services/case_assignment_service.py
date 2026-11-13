from sqlalchemy.orm import Session
from app.models.reviewer import Reviewer
from app.models.case_assignment import CaseAssignment
from app.models.case import Case
from app.services.reviewer_conflict_service import ReviewerConflictService

class CaseAssignmentService:
    """
    Manages reviewer assignments, workload checks, and conflict-of-interest validation.
    Composes ReviewerConflictService to enforce procedural independence.
    """
    def __init__(self, db: Session):
        self.db = db
        self.conflict_service = ReviewerConflictService(db)

    def assign_reviewer(
        self,
        case_id: int,
        reviewer_id: int
    ) -> CaseAssignment:
        case = self.db.query(Case).filter(Case.id == case_id).first()
        if not case:
            raise ValueError("Case does not exist")

        reviewer = self.db.query(Reviewer).filter(Reviewer.id == reviewer_id).first()
        if not reviewer:
            raise ValueError("Reviewer does not exist")

        # 1. Reviewer status check
        if reviewer.status != "ACTIVE":
            raise ValueError("Reviewer is not active")

        # 2. Existing active assignment check
        existing = (
            self.db.query(CaseAssignment)
            .filter(
                CaseAssignment.case_id == case_id,
                CaseAssignment.status == "ACTIVE"
            )
            .first()
        )
        if existing:
            raise ValueError("This case already has an active reviewer")

        # 3. Workload capacity check
        active_case_count = (
            self.db.query(CaseAssignment)
            .filter(
                CaseAssignment.reviewer_id == reviewer_id,
                CaseAssignment.status == "ACTIVE"
            )
            .count()
        )
        if active_case_count >= reviewer.max_active_cases:
            raise ValueError("Reviewer workload capacity reached")

        # 4. Conflict of interest validation
        if self.conflict_service.has_blocking_conflict(reviewer_id, case_id):
            raise ValueError("Reviewer has an unresolved conflict of interest")

        # Assignment is recorded with CLEARED status only after all checks pass
        assignment = CaseAssignment(
            case_id=case_id,
            reviewer_id=reviewer_id,
            conflict_status="CLEARED",
            status="ACTIVE"
        )
        self.db.add(assignment)
        self.db.flush()
        return assignment

    def get_case_assignments(self, case_id: int) -> list[CaseAssignment]:
        return (
            self.db.query(CaseAssignment)
            .filter(CaseAssignment.case_id == case_id)
            .order_by(CaseAssignment.assigned_at.desc())
            .all()
        )
