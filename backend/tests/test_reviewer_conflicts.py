from fastapi.testclient import TestClient
from app.main import app
from app.database.connection import SessionLocal
from app.models import (
    Learner, Assessment, Submission, SimilarityReport, Flag, Reviewer, Case, CaseFlag, ReviewerConflict, CaseAssignment
)
from app.models.integrity_rule import IntegrityRule

client = TestClient(app)

def create_case_and_reviewers():
    db = SessionLocal()
    learner = db.query(Learner).first()
    if not learner:
        learner = Learner(learner_code="LRN-CONF-01", name="Conflict Learner", email="conf_learner@example.com", department="CS")
        db.add(learner)
        db.commit()
        db.refresh(learner)

    assessment = db.query(Assessment).first()
    if not assessment:
        assessment = Assessment(assessment_code="ASM-CONF-01", title="Conflict Assessment", assessment_type="ASSIGNMENT", max_marks=100)
        db.add(assessment)
        db.commit()
        db.refresh(assessment)

    submission = db.query(Submission).first()
    if not submission:
        submission = Submission(
            submission_code="SUB-2026-666001",
            learner_id=learner.id,
            assessment_id=assessment.id,
            version_number=1,
            status="SUBMITTED"
        )
        db.add(submission)
        db.commit()
        db.refresh(submission)

    report = db.query(SimilarityReport).first()
    if not report:
        report = SimilarityReport(
            report_code=f"SIM-{submission.submission_code}-01",
            submission_id=submission.id,
            overall_score=68.0,
            status="COMPLETED"
        )
        db.add(report)
        db.commit()
        db.refresh(report)

    rule = db.query(IntegrityRule).filter_by(
        rule_code="RULE-TEST-CONFLICT"
    ).first()
    if not rule:
        rule = IntegrityRule(
            rule_code="RULE-TEST-CONFLICT",
            rule_name="Conflict Test Rule",
            min_similarity=40,
            max_similarity=69,
            action="REVIEW",
            description="Test rule for reviewer conflict cases"
        )
        db.add(rule)
        db.flush()

    flag_count = db.query(Flag).count()
    flag = Flag(
        flag_code=f"FLG-2026-CONF-{flag_count + 1:04d}",
        submission_id=submission.id,
        report_id=report.id,
        integrity_rule_id=rule.id,
        flag_type="REVIEW",
        status="OPEN"
    )
    db.add(flag)
    db.commit()
    db.refresh(flag)

    # Reviewer 1 (Primary for conflict tests)
    rev1 = db.query(Reviewer).filter_by(reviewer_code="REV-CONF-0001").first()
    if not rev1:
        rev1 = Reviewer(
            reviewer_code="REV-CONF-0001",
            full_name="Prof. Alan Turing",
            email="alan.turing.conf@example.com",
            department="Computer Science",
            max_active_cases=5,
            status="ACTIVE"
        )
        db.add(rev1)
        db.commit()
        db.refresh(rev1)

    # Reviewer 2 (Alternate reviewer)
    rev2 = db.query(Reviewer).filter_by(reviewer_code="REV-CONF-0002").first()
    if not rev2:
        rev2 = Reviewer(
            reviewer_code="REV-CONF-0002",
            full_name="Prof. Ada Lovelace",
            email="ada.lovelace.conf@example.com",
            department="Mathematics",
            max_active_cases=5,
            status="ACTIVE"
        )
        db.add(rev2)
        db.commit()
        db.refresh(rev2)

    # Create Case
    case_count = db.query(Case).count()
    case = Case(
        case_code=f"CASE-2026-{case_count + 1:06d}",
        learner_id=learner.id,
        title="Conflict Test Case",
        status="OPEN"
    )
    db.add(case)
    db.commit()
    db.refresh(case)

    case_id = case.id
    rev1_id = rev1.id
    rev2_id = rev2.id
    db.close()
    return case_id, rev1_id, rev2_id

def test_declare_conflict_pending():
    case_id, rev1_id, _ = create_case_and_reviewers()
    payload = {
        "reviewer_id": rev1_id,
        "case_id": case_id,
        "conflict_type": "PERSONAL",
        "reason": "Personal acquaintance with the learner's family"
    }
    response = client.post("/api/v1/conflicts/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "PENDING"
    assert data["conflict_type"] == "PERSONAL"
    assert data["reviewer_id"] == rev1_id
    assert data["case_id"] == case_id

def test_declare_conflict_nonexistent_reviewer():
    case_id, _, _ = create_case_and_reviewers()
    payload = {
        "reviewer_id": 999999,
        "case_id": case_id,
        "conflict_type": "ACADEMIC",
        "reason": "Graded previous work"
    }
    response = client.post("/api/v1/conflicts/", json=payload)
    assert response.status_code == 400
    assert "Reviewer does not exist" in response.json()["detail"]

def test_declare_conflict_nonexistent_case():
    _, rev1_id, _ = create_case_and_reviewers()
    payload = {
        "reviewer_id": rev1_id,
        "case_id": 999999,
        "conflict_type": "ACADEMIC",
        "reason": "Graded previous work"
    }
    response = client.post("/api/v1/conflicts/", json=payload)
    assert response.status_code == 400
    assert "Case does not exist" in response.json()["detail"]

def test_declare_conflict_without_reason():
    case_id, rev1_id, _ = create_case_and_reviewers()
    payload = {
        "reviewer_id": rev1_id,
        "case_id": case_id,
        "conflict_type": "FINANCIAL",
        "reason": ""  # Invalid empty reason
    }
    response = client.post("/api/v1/conflicts/", json=payload)
    assert response.status_code == 422  # Pydantic min_length=5 validation

def test_assign_reviewer_with_pending_conflict_rejected():
    case_id, rev1_id, _ = create_case_and_reviewers()
    # 1. Declare conflict
    client.post("/api/v1/conflicts/", json={
        "reviewer_id": rev1_id,
        "case_id": case_id,
        "conflict_type": "PROFESSIONAL",
        "reason": "Co-authored previous research paper with learner"
    })

    # 2. Try to assign reviewer -> must be rejected
    assign_res = client.post(
        f"/api/v1/cases/{case_id}/assign",
        json={"reviewer_id": rev1_id}
    )
    assert assign_res.status_code == 400
    assert "unresolved conflict of interest" in assign_res.json()["detail"]

def test_assign_reviewer_with_confirmed_conflict_rejected():
    case_id, rev1_id, _ = create_case_and_reviewers()
    # 1. Declare conflict
    conflict_res = client.post("/api/v1/conflicts/", json={
        "reviewer_id": rev1_id,
        "case_id": case_id,
        "conflict_type": "FINANCIAL",
        "reason": "Financial advisory relationship"
    })
    conflict_id = conflict_res.json()["id"]

    # 2. Confirm conflict
    resolve_res = client.patch(
        f"/api/v1/conflicts/{conflict_id}/resolve",
        json={"decision": "CONFIRMED", "reviewer_admin_id": 1, "review_notes": "Confirmed by ethics chair"}
    )
    assert resolve_res.status_code == 200
    assert resolve_res.json()["status"] == "CONFIRMED"

    # 3. Try to assign -> must be rejected
    assign_res = client.post(
        f"/api/v1/cases/{case_id}/assign",
        json={"reviewer_id": rev1_id}
    )
    assert assign_res.status_code == 400
    assert "unresolved conflict of interest" in assign_res.json()["detail"]

def test_assign_reviewer_after_dismissal_succeeds():
    case_id, rev1_id, _ = create_case_and_reviewers()
    # 1. Declare conflict
    conflict_res = client.post("/api/v1/conflicts/", json={
        "reviewer_id": rev1_id,
        "case_id": case_id,
        "conflict_type": "OTHER",
        "reason": "Mistaken identity reported by reviewer"
    })
    conflict_id = conflict_res.json()["id"]

    # 2. Dismiss conflict
    resolve_res = client.patch(
        f"/api/v1/conflicts/{conflict_id}/resolve",
        json={"decision": "DISMISSED", "reviewer_admin_id": 1, "review_notes": "Claim investigated and dismissed as no connection exists"}
    )
    assert resolve_res.status_code == 200
    assert resolve_res.json()["status"] == "DISMISSED"

    # 3. Assignment should now succeed!
    assign_res = client.post(
        f"/api/v1/cases/{case_id}/assign",
        json={"reviewer_id": rev1_id}
    )
    assert assign_res.status_code == 200
    assert assign_res.json()["status"] == "ASSIGNED"

def test_resolve_same_conflict_twice_rejected():
    case_id, rev1_id, _ = create_case_and_reviewers()
    conflict_res = client.post("/api/v1/conflicts/", json={
        "reviewer_id": rev1_id,
        "case_id": case_id,
        "conflict_type": "ACADEMIC",
        "reason": "Duplicate resolution test"
    })
    conflict_id = conflict_res.json()["id"]

    # First resolution
    res1 = client.patch(
        f"/api/v1/conflicts/{conflict_id}/resolve",
        json={"decision": "DISMISSED", "reviewer_admin_id": 1}
    )
    assert res1.status_code == 200

    # Second resolution -> rejected
    res2 = client.patch(
        f"/api/v1/conflicts/{conflict_id}/resolve",
        json={"decision": "CONFIRMED", "reviewer_admin_id": 1}
    )
    assert res2.status_code == 400
    assert "already been resolved" in res2.json()["detail"]

def test_dismissed_declaration_remains_in_database():
    case_id, rev1_id, _ = create_case_and_reviewers()
    conflict_res = client.post("/api/v1/conflicts/", json={
        "reviewer_id": rev1_id,
        "case_id": case_id,
        "conflict_type": "PERSONAL",
        "reason": "Audit preservation test"
    })
    conflict_id = conflict_res.json()["id"]

    client.patch(
        f"/api/v1/conflicts/{conflict_id}/resolve",
        json={"decision": "DISMISSED", "reviewer_admin_id": 1, "review_notes": "Audit verification note"}
    )

    # Query from database to prove audit preservation
    db = SessionLocal()
    persisted = db.query(ReviewerConflict).filter(ReviewerConflict.id == conflict_id).first()
    assert persisted is not None
    assert persisted.status == "DISMISSED"
    assert persisted.reviewed_at is not None
    assert persisted.reviewed_by == 1
    assert persisted.review_notes == "Audit verification note"
    db.close()

