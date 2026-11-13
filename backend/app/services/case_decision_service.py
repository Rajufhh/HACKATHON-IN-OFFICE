"""
CaseDecisionService — OOP Concept: Composition

This service composes:
  - EvidenceService     (to fetch and validate evidence items)
  - CaseEventService    (to record the audit event)

It does NOT inherit from BaseService because decisions are immutable —
there is no generic update/delete path.

Business rules enforced here:
  1. Case must be in DECISION_PENDING status.
  2. The reviewer must have an ACTIVE, CLEARED assignment to this case.
  3. Rationale must be non-empty.
  4. Evidence IDs must all belong to this case.
  5. The decision snapshot is created atomically with the decision record.
"""

import uuid
from datetime import datetime, timezone

from app.models.case import Case
from app.models.case_assignment import CaseAssignment
from app.models.case_decision import CaseDecision
from app.models.decision_evidence import DecisionEvidence
from app.services.evidence_service import EvidenceService
from app.services.case_event_service import CaseEventService


VALID_OUTCOMES = {
    "BREACH_ESTABLISHED",
    "NO_BREACH",
    "INSUFFICIENT_EVIDENCE",
    "REFERRED_FOR_FURTHER_REVIEW",
}


class CaseDecisionService:
    """
    OOP — Composition:
    CaseDecisionService HAS-A EvidenceService and HAS-A CaseEventService.
    It does not duplicate their logic; it delegates to them.
    """

    def __init__(self, db):
        self.db = db
        # Composed services — injected via constructor (dependency composition)
        self._evidence_svc = EvidenceService(db)
        self._event_svc    = CaseEventService(db)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _generate_decision_code(self) -> str:
        year   = datetime.now(timezone.utc).year
        suffix = uuid.uuid4().hex[:8].upper()
        return f"DEC-{year}-{suffix}"

    def _get_active_cleared_assignment(
        self, case_id: int, reviewer_id: int
    ) -> CaseAssignment | None:
        """Return the assignment only if it is ACTIVE and conflict_status is CLEARED."""
        return (
            self.db.query(CaseAssignment)
            .filter(
                CaseAssignment.case_id    == case_id,
                CaseAssignment.reviewer_id == reviewer_id,
                CaseAssignment.status      == "ACTIVE",
                CaseAssignment.conflict_status == "CLEARED",
            )
            .first()
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def record_decision(
        self,
        case_id: int,
        reviewer_id: int,
        outcome: str,
        rationale: str,
        evidence_ids: list[int],
    ) -> CaseDecision:
        """
        Record a human decision on a case.

        Parameters
        ----------
        case_id      : The case being decided.
        reviewer_id  : The reviewer recording the decision.
        outcome      : One of VALID_OUTCOMES.
        rationale    : Non-empty text explaining the reasoning.
        evidence_ids : IDs of evidence items considered (snapshot taken now).

        Returns
        -------
        CaseDecision instance (not yet committed — caller commits).
        """

        # --- Rule 1: outcome must be valid ---
        outcome = outcome.upper().strip()
        if outcome not in VALID_OUTCOMES:
            raise ValueError(
                f"Invalid outcome '{outcome}'. Allowed: {sorted(VALID_OUTCOMES)}"
            )

        # --- Rule 2: rationale must not be blank ---
        rationale = rationale.strip()
        if not rationale:
            raise ValueError("Decision rationale cannot be blank.")

        # --- Rule 3: case must exist and be DECISION_PENDING ---
        case = self.db.query(Case).filter(Case.id == case_id).first()
        if not case:
            raise ValueError(f"Case {case_id} not found.")
        if case.status != "DECISION_PENDING":
            raise ValueError(
                f"Case {case_id} is in status '{case.status}'. "
                "A decision can only be recorded when status is DECISION_PENDING."
            )

        # --- Rule 4: reviewer must have ACTIVE + CLEARED assignment ---
        assignment = self._get_active_cleared_assignment(case_id, reviewer_id)
        if not assignment:
            raise ValueError(
                f"Reviewer {reviewer_id} does not have an ACTIVE, CLEARED assignment "
                f"to case {case_id}. Decision rejected."
            )

        # --- Rule 5: validate evidence items belong to this case ---
        evidence_items = self._evidence_svc.get_evidence_by_ids(evidence_ids)
        found_ids = {e.id for e in evidence_items}
        for eid in evidence_ids:
            if eid not in found_ids:
                raise ValueError(f"Evidence item {eid} not found.")
            item = next(e for e in evidence_items if e.id == eid)
            if item.case_id != case_id:
                raise ValueError(
                    f"Evidence item {eid} belongs to case {item.case_id}, "
                    f"not case {case_id}. Cross-case evidence is not allowed."
                )

        # --- Create the decision record ---
        decision = CaseDecision(
            decision_code=self._generate_decision_code(),
            case_id=case_id,
            reviewer_id=reviewer_id,
            outcome=outcome,
            rationale=rationale,
        )
        self.db.add(decision)
        self.db.flush()   # get decision.id before creating snapshot rows

        # --- Create immutable snapshot rows (one per evidence item) ---
        for item in evidence_items:
            snap = DecisionEvidence(
                decision_id=decision.id,
                evidence_id=item.id,
                # Snapshot: copied AT decision time, never updated
                evidence_code_snapshot=item.evidence_code,
                evidence_title_snapshot=item.title,
                evidence_type_snapshot=item.evidence_type,
            )
            self.db.add(snap)

        # --- Audit event ---
        self._event_svc.record_event(
            case_id=case_id,
            event_type="DECISION_RECORDED",
            description=(
                f"Decision recorded by reviewer {reviewer_id}: {outcome}. "
                f"Evidence items considered: {len(evidence_items)}."
            ),
            actor_id=reviewer_id,
        )

        self.db.flush()
        return decision

    def get_case_decisions(self, case_id: int) -> list[CaseDecision]:
        """All decisions for a case, oldest first."""
        return (
            self.db.query(CaseDecision)
            .filter(CaseDecision.case_id == case_id)
            .order_by(CaseDecision.decided_at.asc())
            .all()
        )

    def get_decision_by_id(self, decision_id: int) -> CaseDecision | None:
        return (
            self.db.query(CaseDecision)
            .filter(CaseDecision.id == decision_id)
            .first()
        )

