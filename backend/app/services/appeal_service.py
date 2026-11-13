from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.appeal import Appeal
from app.models.appeal_evidence import AppealEvidence
from app.models.appeal_event import AppealEvent
from app.models.case_decision import CaseDecision
from app.models.evidence_item import EvidenceItem
from app.services.appeal_assignment_service import AppealAssignmentService
from app.services.appeal_event_service import AppealEventService
from app.services.appeal_lifecycle_service import AppealLifecycleService


VALID_APPEAL_OUTCOMES = {
    "UPHELD",
    "OVERTURNED",
    "REMANDED",
}


class AppealService:
    """Coordinates appeal submission, evidence, assignment and resolution."""

    def __init__(self, db: Session):
        self.db = db
        self.events = AppealEventService(db)
        self.assignment = AppealAssignmentService(db)
        self.lifecycle = AppealLifecycleService()

    def _generate_appeal_code(self, case_id: int) -> str:
        existing_count = (
            self.db.query(Appeal)
            .join(CaseDecision, Appeal.decision_id == CaseDecision.id)
            .filter(CaseDecision.case_id == case_id)
            .count()
        )
        return f"APL-{case_id:06d}-{existing_count + 1:02d}"

    def get_appeal(self, appeal_id: int) -> Appeal | None:
        return self.db.query(Appeal).filter(Appeal.id == appeal_id).first()

    def submit_appeal(
        self,
        decision_id: int,
        learner_id: int,
        grounds: str,
        evidence_ids: list[int] | None = None,
    ) -> Appeal:
        grounds = grounds.strip()
        if not 10 <= len(grounds) <= 10000:
            raise ValueError(
                "Appeal grounds must contain between 10 and 10000 characters."
            )

        decision = (
            self.db.query(CaseDecision)
            .filter(CaseDecision.id == decision_id)
            .first()
        )
        if not decision:
            raise ValueError("Original decision not found.")
        if decision.case.learner_id != learner_id:
            raise ValueError("Learner does not belong to the original case.")

        existing = (
            self.db.query(Appeal)
            .filter(Appeal.decision_id == decision_id)
            .first()
        )
        if existing:
            raise ValueError("An appeal already exists for this decision.")

        appeal = Appeal(
            appeal_code=self._generate_appeal_code(decision.case_id),
            decision_id=decision_id,
            learner_id=learner_id,
            grounds=grounds,
            status="SUBMITTED",
        )
        self.db.add(appeal)
        self.db.flush()
        self.events.record_event(
            appeal_id=appeal.id,
            event_type="APPEAL_SUBMITTED",
            description=(
                f"Learner {learner_id} submitted an appeal "
                f"against decision {decision_id}."
            ),
            actor_id=learner_id,
            actor_role="LEARNER",
        )

        for evidence_id in evidence_ids or []:
            self.add_evidence(
                appeal_id=appeal.id,
                evidence_id=evidence_id,
                added_by=learner_id,
                actor_role="LEARNER",
            )

        self.db.flush()
        return appeal

    def add_evidence(
        self,
        appeal_id: int,
        evidence_id: int,
        added_by: int | None = None,
        actor_role: str | None = None,
    ) -> AppealEvidence:
        appeal = self.get_appeal(appeal_id)
        if not appeal:
            raise ValueError("Appeal not found.")
        if appeal.status not in {"SUBMITTED", "UNDER_REVIEW"}:
            raise ValueError("Evidence cannot be added to a completed appeal.")

        evidence = (
            self.db.query(EvidenceItem)
            .filter(EvidenceItem.id == evidence_id)
            .first()
        )
        if not evidence:
            raise ValueError("Evidence item not found.")
        if evidence.case_id != appeal.decision.case_id:
            raise ValueError("Evidence must belong to the original case.")

        existing = (
            self.db.query(AppealEvidence)
            .filter(
                AppealEvidence.appeal_id == appeal_id,
                AppealEvidence.evidence_id == evidence_id,
            )
            .first()
        )
        if existing:
            raise ValueError("Evidence is already attached to this appeal.")

        snapshot = AppealEvidence(
            appeal_id=appeal_id,
            evidence_id=evidence.id,
            evidence_code_snapshot=evidence.evidence_code,
            evidence_title_snapshot=evidence.title,
            evidence_type_snapshot=evidence.evidence_type,
            added_by=added_by,
        )
        self.db.add(snapshot)
        self.events.record_event(
            appeal_id=appeal_id,
            event_type="APPEAL_EVIDENCE_ADDED",
            description=(
                f"Evidence {evidence.evidence_code} was attached to the appeal."
            ),
            actor_id=added_by,
            actor_role=actor_role,
        )
        self.db.flush()
        return snapshot

    def assign_reviewer(
        self,
        appeal_id: int,
        reviewer_id: int,
        actor_id: int | None = None,
    ) -> Appeal:
        return self.assignment.assign_reviewer(
            appeal_id=appeal_id,
            reviewer_id=reviewer_id,
            actor_id=actor_id,
        )

    def resolve_appeal(
        self,
        appeal_id: int,
        reviewer_id: int,
        outcome: str,
        rationale: str,
    ) -> Appeal:
        appeal = self.get_appeal(appeal_id)
        if not appeal:
            raise ValueError("Appeal not found.")
        if appeal.status != "UNDER_REVIEW":
            raise ValueError("Appeal must be under review before resolution.")
        if appeal.assigned_reviewer_id != reviewer_id:
            raise ValueError(
                "Only the assigned independent reviewer can resolve this appeal."
            )

        outcome = outcome.upper().strip()
        if outcome not in VALID_APPEAL_OUTCOMES:
            raise ValueError("Invalid appeal outcome.")
        rationale = rationale.strip()
        if not 10 <= len(rationale) <= 10000:
            raise ValueError(
                "Outcome rationale must contain between 10 and 10000 characters."
            )

        appeal.outcome = outcome
        appeal.outcome_rationale = rationale
        appeal.resolved_at = datetime.now(timezone.utc)
        self.lifecycle.transition(appeal, "DECIDED")
        self.events.record_event(
            appeal_id=appeal_id,
            event_type="APPEAL_DECIDED",
            description=(
                f"Appeal resolved with outcome {outcome}. "
                f"Rationale: {rationale}"
            ),
            actor_id=reviewer_id,
            actor_role="INDEPENDENT_REVIEWER",
        )
        self.db.flush()
        return appeal

    def withdraw_appeal(self, appeal_id: int, learner_id: int) -> Appeal:
        appeal = self.get_appeal(appeal_id)
        if not appeal:
            raise ValueError("Appeal not found.")
        if appeal.learner_id != learner_id:
            raise ValueError(
                "Only the learner who submitted the appeal can withdraw it."
            )

        self.lifecycle.transition(appeal, "WITHDRAWN")
        self.events.record_event(
            appeal_id=appeal_id,
            event_type="APPEAL_WITHDRAWN",
            description="Learner withdrew the appeal.",
            actor_id=learner_id,
            actor_role="LEARNER",
        )
        self.db.flush()
        return appeal

    def list_appeals(self, status: str | None = None) -> list[Appeal]:
        query = self.db.query(Appeal)
        if status:
            query = query.filter(Appeal.status == status)
        return query.order_by(Appeal.submitted_at.desc()).all()

    def get_events(self, appeal_id: int) -> list[AppealEvent]:
        if not self.get_appeal(appeal_id):
            raise ValueError("Appeal not found.")
        return self.events.get_events(appeal_id)
