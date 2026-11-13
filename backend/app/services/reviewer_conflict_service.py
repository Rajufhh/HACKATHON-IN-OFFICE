from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.reviewer import Reviewer
from app.models.case import Case
from app.models.reviewer_conflict import ReviewerConflict

class ReviewerConflictService:
    """
    Manages conflict-of-interest declarations, eligibility checks, and resolutions.
    Enforces independence: PENDING or CONFIRMED declarations block reviewer assignment.
    """
    BLOCKING_STATUSES = {"PENDING", "CONFIRMED"}

    def __init__(self, db: Session):
        self.db = db

    def declare_conflict(
        self,
        reviewer_id: int,
        case_id: int,
        conflict_type: str,
        reason: str
    ) -> ReviewerConflict:
        reviewer = self.db.query(Reviewer).filter(Reviewer.id == reviewer_id).first()
        if not reviewer:
            raise ValueError("Reviewer does not exist")

        case = self.db.query(Case).filter(Case.id == case_id).first()
        if not case:
            raise ValueError("Case does not exist")

        if not reason or not reason.strip():
            raise ValueError("A documented reason is required to declare a conflict of interest")

        conflict = ReviewerConflict(
            reviewer_id=reviewer_id,
            case_id=case_id,
            conflict_type=conflict_type,
            reason=reason.strip(),
            status="PENDING"
        )
        self.db.add(conflict)
        self.db.flush()
        return conflict

    def has_blocking_conflict(self, reviewer_id: int, case_id: int) -> bool:
        """
        Returns True if a pending or confirmed conflict blocks this reviewer.
        """
        count = (
            self.db.query(ReviewerConflict)
            .filter(
                ReviewerConflict.reviewer_id == reviewer_id,
                ReviewerConflict.case_id == case_id,
                ReviewerConflict.status.in_(self.BLOCKING_STATUSES)
            )
            .count()
        )
        return count > 0

    def resolve_conflict(
        self,
        conflict_id: int,
        decision: str,
        reviewer_admin_id: int,
        review_notes: str | None = None
    ) -> ReviewerConflict:
        conflict = self.db.query(ReviewerConflict).filter(ReviewerConflict.id == conflict_id).first()
        if not conflict:
            raise ValueError("Conflict record does not exist")

        if conflict.status in {"CONFIRMED", "DISMISSED", "WITHDRAWN"}:
            raise ValueError(f"Conflict has already been resolved with status {conflict.status}")

        if decision not in {"CONFIRMED", "DISMISSED"}:
            raise ValueError("Invalid decision; must be CONFIRMED or DISMISSED")

        conflict.status = decision
        conflict.reviewed_at = datetime.now(timezone.utc)
        conflict.reviewed_by = reviewer_admin_id
        conflict.review_notes = review_notes

        self.db.flush()
        return conflict

    def get_conflicts_for_case(self, case_id: int) -> list[ReviewerConflict]:
        return (
            self.db.query(ReviewerConflict)
            .filter(ReviewerConflict.case_id == case_id)
            .order_by(ReviewerConflict.declared_at.desc())
            .all()
        )

    def get_conflicts_for_reviewer(self, reviewer_id: int) -> list[ReviewerConflict]:
        return (
            self.db.query(ReviewerConflict)
            .filter(ReviewerConflict.reviewer_id == reviewer_id)
            .order_by(ReviewerConflict.declared_at.desc())
            .all()
        )

