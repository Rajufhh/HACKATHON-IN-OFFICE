import uuid

import pytest
from fastapi.testclient import TestClient

from app.database.connection import SessionLocal
from app.main import app
from app.models import (
    Appeal,
    AppealEvent,
    AppealEvidence,
    Case,
    CaseAssignment,
    CaseDecision,
    DecisionEvidence,
    EvidenceItem,
    Learner,
    Reviewer,
    ReviewerConflict,
)


client = TestClient(app)


@pytest.fixture
def appeal_context():
    token = uuid.uuid4().hex.upper()
    db = SessionLocal()
    try:
        learner = Learner(
            learner_code=f"APL-L-{token[:20]}",
            name="Appeal Test Learner",
            email=f"appeal-learner-{token}@example.com",
            department="Computer Science",
        )
        other_learner = Learner(
            learner_code=f"APL-OL-{token[:20]}",
            name="Other Appeal Learner",
            email=f"appeal-other-{token}@example.com",
            department="Mathematics",
        )
        original_reviewer = Reviewer(
            reviewer_code=f"APL-OR-{token[:20]}",
            full_name="Original Decision Reviewer",
            email=f"appeal-original-{token}@example.com",
            department="Computer Science",
            max_active_cases=10,
            status="ACTIVE",
        )
        independent_reviewer = Reviewer(
            reviewer_code=f"APL-IR-{token[:20]}",
            full_name="Independent Appeal Reviewer",
            email=f"appeal-independent-{token}@example.com",
            department="Mathematics",
            max_active_cases=10,
            status="ACTIVE",
        )
        inactive_reviewer = Reviewer(
            reviewer_code=f"APL-IN-{token[:20]}",
            full_name="Inactive Appeal Reviewer",
            email=f"appeal-inactive-{token}@example.com",
            department="Biology",
            max_active_cases=10,
            status="INACTIVE",
        )
        assigned_reviewer = Reviewer(
            reviewer_code=f"APL-AS-{token[:20]}",
            full_name="Original Case Reviewer",
            email=f"appeal-assigned-{token}@example.com",
            department="Physics",
            max_active_cases=10,
            status="ACTIVE",
        )
        conflict_reviewer = Reviewer(
            reviewer_code=f"APL-CO-{token[:20]}",
            full_name="Conflicted Appeal Reviewer",
            email=f"appeal-conflict-{token}@example.com",
            department="Chemistry",
            max_active_cases=10,
            status="ACTIVE",
        )
        capacity_reviewer = Reviewer(
            reviewer_code=f"APL-CA-{token[:20]}",
            full_name="At Capacity Appeal Reviewer",
            email=f"appeal-capacity-{token}@example.com",
            department="History",
            max_active_cases=1,
            status="ACTIVE",
        )
        db.add_all([
            learner,
            other_learner,
            original_reviewer,
            independent_reviewer,
            inactive_reviewer,
            assigned_reviewer,
            conflict_reviewer,
            capacity_reviewer,
        ])
        db.flush()

        case = Case(
            case_code=f"APL-CASE-{token}",
            learner_id=learner.id,
            title="Appeal fixture case",
            status="DECISION_PENDING",
        )
        other_case = Case(
            case_code=f"APL-OTHER-{token}",
            learner_id=other_learner.id,
            title="Other appeal fixture case",
            status="OPEN",
        )
        db.add_all([case, other_case])
        db.flush()

        decision = CaseDecision(
            decision_code=f"APL-DEC-{token}",
            case_id=case.id,
            reviewer_id=original_reviewer.id,
            outcome="BREACH_ESTABLISHED",
            rationale="Original decision fixture rationale.",
        )
        db.add(decision)
        db.flush()

        evidence = EvidenceItem(
            evidence_code=f"APL-EVD-{token}",
            case_id=case.id,
            evidence_type="DOCUMENT",
            title="Original case evidence",
        )
        other_evidence = EvidenceItem(
            evidence_code=f"APL-XEVD-{token}",
            case_id=other_case.id,
            evidence_type="DOCUMENT",
            title="Evidence from another case",
        )
        db.add_all([evidence, other_evidence])
        db.flush()
        evidence_snapshot = DecisionEvidence(
            decision_id=decision.id,
            evidence_id=evidence.id,
            evidence_code_snapshot=evidence.evidence_code,
            evidence_title_snapshot=evidence.title,
            evidence_type_snapshot=evidence.evidence_type,
        )
        db.add(evidence_snapshot)

        db.add_all([
            CaseAssignment(
                case_id=case.id,
                reviewer_id=assigned_reviewer.id,
                conflict_status="CLEARED",
                status="ACTIVE",
            ),
            CaseAssignment(
                case_id=other_case.id,
                reviewer_id=capacity_reviewer.id,
                conflict_status="CLEARED",
                status="ACTIVE",
            ),
            ReviewerConflict(
                reviewer_id=conflict_reviewer.id,
                case_id=case.id,
                conflict_type="ACADEMIC",
                reason="Test conflict for appeal assignment.",
                status="PENDING",
            ),
        ])
        db.commit()

        context = {
            "case_id": case.id,
            "other_case_id": other_case.id,
            "decision_id": decision.id,
            "learner_id": learner.id,
            "other_learner_id": other_learner.id,
            "original_reviewer_id": original_reviewer.id,
            "independent_reviewer_id": independent_reviewer.id,
            "inactive_reviewer_id": inactive_reviewer.id,
            "assigned_reviewer_id": assigned_reviewer.id,
            "conflict_reviewer_id": conflict_reviewer.id,
            "capacity_reviewer_id": capacity_reviewer.id,
            "evidence_id": evidence.id,
            "other_evidence_id": other_evidence.id,
            "decision_rationale": decision.rationale,
            "decision_snapshot": (
                evidence_snapshot.evidence_code_snapshot,
                evidence_snapshot.evidence_title_snapshot,
                evidence_snapshot.evidence_type_snapshot,
            ),
            "reviewer_ids": [
                original_reviewer.id,
                independent_reviewer.id,
                inactive_reviewer.id,
                assigned_reviewer.id,
                conflict_reviewer.id,
                capacity_reviewer.id,
            ],
        }
    finally:
        db.close()

    try:
        yield context
    finally:
        cleanup_db = SessionLocal()
        try:
            appeal_ids = [
                row[0]
                for row in cleanup_db.query(Appeal.id)
                .filter(Appeal.decision_id == context["decision_id"])
                .all()
            ]
            if appeal_ids:
                cleanup_db.query(AppealEvidence).filter(
                    AppealEvidence.appeal_id.in_(appeal_ids)
                ).delete(synchronize_session=False)
                cleanup_db.query(AppealEvent).filter(
                    AppealEvent.appeal_id.in_(appeal_ids)
                ).delete(synchronize_session=False)
                cleanup_db.query(Appeal).filter(
                    Appeal.id.in_(appeal_ids)
                ).delete(synchronize_session=False)

            cleanup_db.query(ReviewerConflict).filter(
                ReviewerConflict.case_id == context["case_id"]
            ).delete(synchronize_session=False)
            cleanup_db.query(CaseAssignment).filter(
                CaseAssignment.case_id.in_([
                    context["case_id"],
                    context["other_case_id"],
                ])
            ).delete(synchronize_session=False)
            cleanup_db.query(DecisionEvidence).filter(
                DecisionEvidence.decision_id == context["decision_id"]
            ).delete(synchronize_session=False)
            cleanup_db.query(CaseDecision).filter(
                CaseDecision.id == context["decision_id"]
            ).delete(synchronize_session=False)
            cleanup_db.query(EvidenceItem).filter(
                EvidenceItem.case_id.in_([
                    context["case_id"],
                    context["other_case_id"],
                ])
            ).delete(synchronize_session=False)
            cleanup_db.query(Case).filter(
                Case.id.in_([
                    context["case_id"],
                    context["other_case_id"],
                ])
            ).delete(synchronize_session=False)
            cleanup_db.query(Learner).filter(
                Learner.id.in_([
                    context["learner_id"],
                    context["other_learner_id"],
                ])
            ).delete(synchronize_session=False)
            cleanup_db.query(Reviewer).filter(
                Reviewer.id.in_(context["reviewer_ids"])
            ).delete(synchronize_session=False)
            cleanup_db.commit()
        finally:
            cleanup_db.close()


def _submit_appeal(
    context: dict,
    *,
    decision_id: int | None = None,
    learner_id: int | None = None,
    grounds: str = "The original decision did not consider all relevant context.",
    evidence_ids: list[int] | None = None,
):
    return client.post("/api/v1/appeals/", json={
        "decision_id": (
            context["decision_id"] if decision_id is None else decision_id
        ),
        "learner_id": (
            context["learner_id"] if learner_id is None else learner_id
        ),
        "grounds": grounds,
        "evidence_ids": evidence_ids or [],
    })


def _appeal_id(context: dict) -> int:
    response = _submit_appeal(context)
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_submit_appeal_records_event_and_preserves_original_decision(appeal_context):
    response = _submit_appeal(appeal_context)
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["status"] == "SUBMITTED"
    assert data["outcome"] is None

    events_response = client.get(f"/api/v1/appeals/{data['id']}/events")
    assert events_response.status_code == 200
    assert [event["event_type"] for event in events_response.json()] == [
        "APPEAL_SUBMITTED"
    ]

    with SessionLocal() as db:
        decision = db.query(CaseDecision).filter_by(
            id=appeal_context["decision_id"]
        ).one()
        snapshot = db.query(DecisionEvidence).filter_by(
            decision_id=appeal_context["decision_id"]
        ).one()
        assert decision.rationale == appeal_context["decision_rationale"]
        assert decision.outcome == "BREACH_ESTABLISHED"
        assert (
            snapshot.evidence_code_snapshot,
            snapshot.evidence_title_snapshot,
            snapshot.evidence_type_snapshot,
        ) == appeal_context["decision_snapshot"]


def test_submit_appeal_rejects_missing_decision(appeal_context):
    response = _submit_appeal(appeal_context, decision_id=999999999)
    assert response.status_code == 422
    assert response.json()["detail"] == "Original decision not found."


def test_submit_appeal_rejects_learner_not_on_case(appeal_context):
    response = _submit_appeal(
        appeal_context,
        learner_id=appeal_context["other_learner_id"],
    )
    assert response.status_code == 422
    assert "does not belong" in response.json()["detail"]


def test_only_one_appeal_can_be_submitted_for_a_decision(appeal_context):
    first_response = _submit_appeal(appeal_context)
    assert first_response.status_code == 201, first_response.text

    second_response = _submit_appeal(appeal_context)
    assert second_response.status_code == 422
    assert "already exists" in second_response.json()["detail"]


def test_submit_appeal_rejects_blank_grounds(appeal_context):
    response = _submit_appeal(appeal_context, grounds="          ")
    assert response.status_code == 422
    assert "grounds" in response.json()["detail"].lower()


@pytest.mark.parametrize(
    ("reviewer_key", "message"),
    [
        ("original_reviewer_id", "Original decision-maker"),
        ("inactive_reviewer_id", "not active"),
        ("assigned_reviewer_id", "already assigned"),
        ("conflict_reviewer_id", "conflict"),
        ("capacity_reviewer_id", "workload capacity"),
    ],
)
def test_assignment_rejects_ineligible_reviewers(
    appeal_context,
    reviewer_key,
    message,
):
    appeal_id = _appeal_id(appeal_context)
    response = client.post(
        f"/api/v1/appeals/{appeal_id}/assign",
        json={"reviewer_id": appeal_context[reviewer_key]},
    )
    assert response.status_code == 422
    assert message.lower() in response.json()["detail"].lower()


def test_assignment_rejects_missing_reviewer(appeal_context):
    appeal_id = _appeal_id(appeal_context)
    response = client.post(
        f"/api/v1/appeals/{appeal_id}/assign",
        json={"reviewer_id": 999999999},
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "Reviewer not found."


def test_assign_independent_reviewer_moves_appeal_under_review(appeal_context):
    appeal_id = _appeal_id(appeal_context)
    response = client.post(
        f"/api/v1/appeals/{appeal_id}/assign",
        json={
            "reviewer_id": appeal_context["independent_reviewer_id"],
            "actor_id": appeal_context["original_reviewer_id"],
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "UNDER_REVIEW"
    assert response.json()["assigned_reviewer_id"] == (
        appeal_context["independent_reviewer_id"]
    )

    events = client.get(f"/api/v1/appeals/{appeal_id}/events").json()
    assert [event["event_type"] for event in events] == [
        "APPEAL_SUBMITTED",
        "REVIEWER_ASSIGNED",
    ]


def test_appeal_cannot_be_resolved_before_assignment(appeal_context):
    appeal_id = _appeal_id(appeal_context)
    response = client.post(
        f"/api/v1/appeals/{appeal_id}/resolve",
        json={
            "reviewer_id": appeal_context["independent_reviewer_id"],
            "outcome": "UPHELD",
            "rationale": "The appeal was carefully reviewed.",
        },
    )
    assert response.status_code == 422
    assert "under review" in response.json()["detail"].lower()


def test_only_assigned_reviewer_can_resolve_appeal(appeal_context):
    appeal_id = _appeal_id(appeal_context)
    assignment = client.post(
        f"/api/v1/appeals/{appeal_id}/assign",
        json={"reviewer_id": appeal_context["independent_reviewer_id"]},
    )
    assert assignment.status_code == 200, assignment.text

    response = client.post(
        f"/api/v1/appeals/{appeal_id}/resolve",
        json={
            "reviewer_id": appeal_context["original_reviewer_id"],
            "outcome": "UPHELD",
            "rationale": "The appeal was carefully reviewed.",
        },
    )
    assert response.status_code == 422
    assert "assigned independent reviewer" in response.json()["detail"]


def test_resolve_appeal_records_outcome_without_changing_decision(appeal_context):
    appeal_id = _appeal_id(appeal_context)
    reviewer_id = appeal_context["independent_reviewer_id"]
    assignment = client.post(
        f"/api/v1/appeals/{appeal_id}/assign",
        json={"reviewer_id": reviewer_id},
    )
    assert assignment.status_code == 200, assignment.text

    response = client.post(
        f"/api/v1/appeals/{appeal_id}/resolve",
        json={
            "reviewer_id": reviewer_id,
            "outcome": "OVERTURNED",
            "rationale": "The appeal provided material context not previously considered.",
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "DECIDED"
    assert response.json()["outcome"] == "OVERTURNED"

    with SessionLocal() as db:
        decision = db.query(CaseDecision).filter_by(
            id=appeal_context["decision_id"]
        ).one()
        snapshot = db.query(DecisionEvidence).filter_by(
            decision_id=appeal_context["decision_id"]
        ).one()
        assert decision.rationale == appeal_context["decision_rationale"]
        assert decision.outcome == "BREACH_ESTABLISHED"
        assert (
            snapshot.evidence_code_snapshot,
            snapshot.evidence_title_snapshot,
            snapshot.evidence_type_snapshot,
        ) == appeal_context["decision_snapshot"]


def test_resolve_appeal_rejects_blank_rationale(appeal_context):
    appeal_id = _appeal_id(appeal_context)
    reviewer_id = appeal_context["independent_reviewer_id"]
    assignment = client.post(
        f"/api/v1/appeals/{appeal_id}/assign",
        json={"reviewer_id": reviewer_id},
    )
    assert assignment.status_code == 200, assignment.text

    response = client.post(
        f"/api/v1/appeals/{appeal_id}/resolve",
        json={
            "reviewer_id": reviewer_id,
            "outcome": "UPHELD",
            "rationale": "          ",
        },
    )
    assert response.status_code == 422


def test_appeal_evidence_must_belong_to_original_case(appeal_context):
    appeal_id = _appeal_id(appeal_context)
    response = client.post(
        f"/api/v1/appeals/{appeal_id}/evidence",
        json={"evidence_id": appeal_context["other_evidence_id"]},
    )
    assert response.status_code == 422
    assert "original case" in response.json()["detail"]


def test_appeal_evidence_is_snapshotted_and_cannot_be_duplicated(appeal_context):
    appeal_id = _appeal_id(appeal_context)
    payload = {"evidence_id": appeal_context["evidence_id"]}
    first_response = client.post(
        f"/api/v1/appeals/{appeal_id}/evidence",
        json=payload,
    )
    assert first_response.status_code == 201, first_response.text
    assert first_response.json()["evidence_title_snapshot"] == (
        "Original case evidence"
    )

    duplicate_response = client.post(
        f"/api/v1/appeals/{appeal_id}/evidence",
        json=payload,
    )
    assert duplicate_response.status_code == 422
    assert "already attached" in duplicate_response.json()["detail"]


def test_learner_can_withdraw_submitted_appeal(appeal_context):
    appeal_id = _appeal_id(appeal_context)
    response = client.post(
        f"/api/v1/appeals/{appeal_id}/withdraw",
        params={"learner_id": appeal_context["learner_id"]},
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "WITHDRAWN"


def test_decided_appeal_cannot_be_withdrawn(appeal_context):
    appeal_id = _appeal_id(appeal_context)
    reviewer_id = appeal_context["independent_reviewer_id"]
    assignment = client.post(
        f"/api/v1/appeals/{appeal_id}/assign",
        json={"reviewer_id": reviewer_id},
    )
    assert assignment.status_code == 200, assignment.text
    resolution = client.post(
        f"/api/v1/appeals/{appeal_id}/resolve",
        json={
            "reviewer_id": reviewer_id,
            "outcome": "REMANDED",
            "rationale": "The case should be reconsidered with additional context.",
        },
    )
    assert resolution.status_code == 200, resolution.text

    response = client.post(
        f"/api/v1/appeals/{appeal_id}/withdraw",
        params={"learner_id": appeal_context["learner_id"]},
    )
    assert response.status_code == 422


def test_appeal_detail_list_and_event_endpoints(appeal_context):
    appeal_id = _appeal_id(appeal_context)

    detail = client.get(f"/api/v1/appeals/{appeal_id}")
    assert detail.status_code == 200, detail.text
    assert detail.json()["id"] == appeal_id
    assert len(detail.json()["events"]) == 1
    assert detail.json()["evidence_snapshots"] == []

    listed = client.get("/api/v1/appeals/", params={"status": "SUBMITTED"})
    assert listed.status_code == 200
    assert any(appeal["id"] == appeal_id for appeal in listed.json())

    events = client.get(f"/api/v1/appeals/{appeal_id}/events")
    assert events.status_code == 200
    assert events.json()[0]["event_type"] == "APPEAL_SUBMITTED"


def test_missing_appeal_returns_not_found(appeal_context):
    assert client.get("/api/v1/appeals/999999999").status_code == 404
    assert client.get("/api/v1/appeals/999999999/events").status_code == 404
