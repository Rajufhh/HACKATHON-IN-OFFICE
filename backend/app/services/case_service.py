from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.models.case import Case
from app.models.flag import Flag
from app.models.case_flag import CaseFlag
from app.services.case_event_service import CaseEventService
from app.services.case_lifecycle_service import CaseLifecycleService
from app.services.case_assignment_service import CaseAssignmentService

class CaseService:
    """
    Main Case Management Coordinator using OOP Composition:
    - Composes CaseEventService for immutable event logging
    - Composes CaseLifecycleService for transition enforcement
    - Composes CaseAssignmentService for reviewer and conflict checks
    """
    def __init__(self, db: Session):
        self.db = db
        self.event_service = CaseEventService(db)
        self.lifecycle_service = CaseLifecycleService()
        self.assignment_service = CaseAssignmentService(db)

    def create_case(
        self,
        case_code: str,
        flag_id: int,
        title: str,
        description: str | None = None,
        actor_id: int | None = None
    ) -> Case:
        flag = self.db.query(Flag).filter(Flag.id == flag_id).first()
        if not flag:
            raise ValueError("Flag does not exist")

        # Check if flag is already linked to a case
        existing_case_flag = self.db.query(CaseFlag).filter(CaseFlag.flag_id == flag_id).first()
        if existing_case_flag:
            raise ValueError("Flag is already linked to an existing case")

        # Get learner_id from flag's submission
        if not flag.submission:
            raise ValueError("Flag does not have an associated submission")
        learner_id = flag.submission.learner_id

        # Create Case
        case = Case(
            case_code=case_code,
            learner_id=learner_id,
            title=title,
            description=description,
            status="OPEN",
            priority="NORMAL"
        )
        self.db.add(case)
        try:
            self.db.flush()
        except IntegrityError:
            self.db.rollback()
            raise ValueError(f"Case with code {case_code} already exists")

        # Link CaseFlag
        case_flag = CaseFlag(case_id=case.id, flag_id=flag.id)
        self.db.add(case_flag)

        # Update flag status to UNDER_REVIEW
        flag.status = "UNDER_REVIEW"

        # Record case creation event
        self.event_service.record_event(
            case_id=case.id,
            event_type="CASE_OPENED",
            description=f"Case {case_code} opened from Flag {flag.flag_code}: {title}",
            actor_id=actor_id
        )

        self.db.commit()
        self.db.refresh(case)
        return case

    def update_case_status(
        self,
        case_id: int,
        new_status: str,
        reason: str | None = None,
        actor_id: int | None = None
    ) -> Case:
        case = self.db.query(Case).filter(Case.id == case_id).first()
        if not case:
            raise ValueError("Case does not exist")

        # Validate transition using lifecycle service
        self.lifecycle_service.validate_transition(case.status, new_status)

        old_status = case.status
        case.status = new_status
        if new_status == "CLOSED":
            case.closed_at = datetime.now(timezone.utc)

        # Record transition event
        self.event_service.record_event(
            case_id=case.id,
            event_type="STATUS_CHANGED",
            description=f"Status changed from {old_status} to {new_status}. {reason or ''}".strip(),
            actor_id=actor_id
        )

        self.db.commit()
        self.db.refresh(case)
        return case

    def assign_reviewer(
        self,
        case_id: int,
        reviewer_id: int,
        actor_id: int | None = None
    ) -> Case:
        case = self.db.query(Case).filter(Case.id == case_id).first()
        if not case:
            raise ValueError("Case does not exist")

        # Assign reviewer via assignment service
        assignment = self.assignment_service.assign_reviewer(case_id, reviewer_id)

        # Transition status to ASSIGNED if currently OPEN
        if case.status == "OPEN":
            self.lifecycle_service.validate_transition(case.status, "ASSIGNED")
            case.status = "ASSIGNED"

        # Record event
        self.event_service.record_event(
            case_id=case.id,
            event_type="REVIEWER_ASSIGNED",
            description=(
                f"Reviewer ID {reviewer_id} assigned to case {case.case_code}. "
                f"Conflict status: {assignment.conflict_status}"
            ),
            actor_id=actor_id
        )

        self.db.commit()
        self.db.refresh(case)
        return case

    def get_case_by_id(self, case_id: int) -> Case | None:
        return self.db.query(Case).filter(Case.id == case_id).first()

    def get_all_cases(self, status: str | None = None) -> list[Case]:
        query = self.db.query(Case)
        if status:
            query = query.filter(Case.status == status)
        return query.order_by(Case.id.desc()).all()

