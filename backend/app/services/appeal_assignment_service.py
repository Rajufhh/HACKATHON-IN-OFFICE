from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.appeal import Appeal
from app.models.case_assignment import CaseAssignment
from app.models.reviewer import Reviewer
from app.models.reviewer_conflict import ReviewerConflict
from app.services.appeal_event_service import AppealEventService
from app.services.appeal_lifecycle_service import AppealLifecycleService


class AppealAssignmentService:
    """Validates and records independent appeal reviewer assignments."""

    def __init__(self, db: Session):
        self.db = db
        self.events = AppealEventService(db)
        self.lifecycle = AppealLifecycleService()

    def assign_reviewer(
        self,
        appeal_id: int,
        reviewer_id: int,
        actor_id: int | None = None,
    ) -> Appeal:
        appeal = self.db.query(Appeal).filter(Appeal.id == appeal_id).first()
        if not appeal:
            raise ValueError("Appeal not found.")
        if appeal.status != "SUBMITTED":
            raise ValueError("Only submitted appeals can be assigned.")

        decision = appeal.decision
        case_id = decision.case_id
        reviewer = (
            self.db.query(Reviewer)
            .filter(Reviewer.id == reviewer_id)
            .first()
        )
        if not reviewer:
            raise ValueError("Reviewer not found.")
        if reviewer.status != "ACTIVE":
            raise ValueError("Reviewer is not active.")
        if reviewer_id == decision.reviewer_id:
            raise ValueError(
                "Original decision-maker cannot review this appeal."
            )

        existing_assignment = (
            self.db.query(CaseAssignment)
            .filter(
                CaseAssignment.case_id == case_id,
                CaseAssignment.reviewer_id == reviewer_id,
                CaseAssignment.status == "ACTIVE",
            )
            .first()
        )
        if existing_assignment:
            raise ValueError(
                "Reviewer is already assigned to the original case."
            )

        conflict = (
            self.db.query(ReviewerConflict)
            .filter(
                ReviewerConflict.case_id == case_id,
                ReviewerConflict.reviewer_id == reviewer_id,
                ReviewerConflict.status.in_(["PENDING", "CONFIRMED"]),
            )
            .first()
        )
        if conflict:
            raise ValueError(
                "Reviewer has an unresolved or confirmed conflict."
            )

        active_case_assignments = (
            self.db.query(CaseAssignment)
            .filter(
                CaseAssignment.reviewer_id == reviewer_id,
                CaseAssignment.status == "ACTIVE",
            )
            .count()
        )
        active_appeals = (
            self.db.query(Appeal)
            .filter(
                Appeal.assigned_reviewer_id == reviewer_id,
                Appeal.status.in_(["SUBMITTED", "UNDER_REVIEW"]),
            )
            .count()
        )
        current_workload = active_case_assignments + active_appeals
        capacity = reviewer.max_active_cases or 0
        if current_workload >= capacity:
            raise ValueError(
                "Reviewer has reached maximum workload capacity."
            )

        appeal.assigned_reviewer_id = reviewer_id
        appeal.assigned_at = datetime.now(timezone.utc)
        self.lifecycle.transition(appeal, "UNDER_REVIEW")
        self.events.record_event(
            appeal_id=appeal.id,
            event_type="REVIEWER_ASSIGNED",
            description=(
                f"Independent appeal reviewer {reviewer_id} assigned."
            ),
            actor_id=actor_id,
            actor_role="ADMIN",
        )
        self.db.flush()
        return appeal
