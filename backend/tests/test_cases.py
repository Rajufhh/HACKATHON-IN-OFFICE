from fastapi.testclient import TestClient
from app.main import app
from app.database.connection import SessionLocal
from app.models import Learner, Assessment, Submission, SimilarityReport, Flag, Reviewer, Case, CaseFlag, CaseEvent
from app.models.integrity_rule import IntegrityRule

client = TestClient(app)

def create_sample_flag():
    db = SessionLocal()
    learner = db.query(Learner).first()
    if not learner:
        learner = Learner(learner_code="LRN-CASE-01", name="Case Learner", email="case_learner@example.com", department="CS")
        db.add(learner)
        db.commit()
        db.refresh(learner)

    assessment = db.query(Assessment).first()
    if not assessment:
        assessment = Assessment(assessment_code="ASM-CASE-01", title="Case Assessment", assessment_type="ASSIGNMENT", max_marks=100)
        db.add(assessment)
        db.commit()
        db.refresh(assessment)

    submission = db.query(Submission).first()
    if not submission:
        submission = Submission(
            submission_code="SUB-2026-777001",
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
            overall_score=75.0,
            status="COMPLETED"
        )
        db.add(report)
        db.commit()
        db.refresh(report)

    rule = db.query(IntegrityRule).filter_by(
        rule_code="RULE-TEST-CASE"
    ).first()
    if not rule:
        rule = IntegrityRule(
            rule_code="RULE-TEST-CASE",
            rule_name="Case Test Rule",
            min_similarity=70,
            max_similarity=100,
            action="PRIORITY_REVIEW",
            description="Test rule for case management"
        )
        db.add(rule)
        db.flush()

    # Create a fresh unique flag
    flag_count = db.query(Flag).count()
    flag = Flag(
        flag_code=f"FLG-2026-CASE-{flag_count + 1:04d}",
        submission_id=submission.id,
        report_id=report.id,
        integrity_rule_id=rule.id,
        flag_type="PRIORITY_REVIEW",
        status="OPEN",
        reason="Test flag for case creation"
    )
    db.add(flag)
    db.commit()
    db.refresh(flag)
    flag_id = flag.id
    db.close()
    return flag_id

def test_create_case_success():
    flag_id = create_sample_flag()
    payload = {
        "case_code": f"CASE-2026-10{flag_id:04d}",
        "flag_id": flag_id,
        "title": "Similarity review for Python assignment",
        "description": "The similarity report requires human examination."
    }
    response = client.post("/api/v1/cases/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["case_code"] == payload["case_code"]
    assert data["status"] == "OPEN"
    assert data["priority"] == "NORMAL"
    assert data["title"] == payload["title"]

    # Verify event was recorded
    case_id = data["id"]
    events_res = client.get(f"/api/v1/cases/{case_id}/events")
    assert events_res.status_code == 200
    events = events_res.json()
    assert len(events) >= 1
    assert events[0]["event_type"] == "CASE_OPENED"

def test_reject_nonexistent_flag():
    payload = {
        "case_code": "CASE-2026-999999",
        "flag_id": 999999,
        "title": "Invalid flag case",
        "description": "Should fail"
    }
    response = client.post("/api/v1/cases/", json=payload)
    assert response.status_code == 400
    assert "Flag does not exist" in response.json()["detail"]

def test_reject_flag_already_linked():
    flag_id = create_sample_flag()
    payload1 = {
        "case_code": f"CASE-2026-20{flag_id:04d}",
        "flag_id": flag_id,
        "title": "First case linking flag",
        "description": "First link"
    }
    res1 = client.post("/api/v1/cases/", json=payload1)
    assert res1.status_code == 201

    payload2 = {
        "case_code": f"CASE-2026-21{flag_id:04d}",
        "flag_id": flag_id,
        "title": "Second case linking same flag",
        "description": "Should fail with 400"
    }
    res2 = client.post("/api/v1/cases/", json=payload2)
    assert res2.status_code == 400
    assert "Flag is already linked to an existing case" in res2.json()["detail"]

def test_invalid_status_transition():
    flag_id = create_sample_flag()
    payload = {
        "case_code": f"CASE-2026-30{flag_id:04d}",
        "flag_id": flag_id,
        "title": "Invalid transition test",
        "description": "Testing OPEN -> CLOSED invalid jump"
    }
    create_res = client.post("/api/v1/cases/", json=payload)
    assert create_res.status_code == 201
    case_id = create_res.json()["id"]

    # Attempt OPEN -> CLOSED directly (invalid)
    transition_res = client.patch(
        f"/api/v1/cases/{case_id}/status",
        json={"status": "CLOSED", "reason": "Jumping directly"}
    )
    assert transition_res.status_code == 400
    assert "Invalid case transition: OPEN -> CLOSED" in transition_res.json()["detail"]

def test_valid_lifecycle_transitions_and_events():
    flag_id = create_sample_flag()
    payload = {
        "case_code": f"CASE-2026-40{flag_id:04d}",
        "flag_id": flag_id,
        "title": "Full lifecycle test",
        "description": "Testing complete state transitions"
    }
    case_id = client.post("/api/v1/cases/", json=payload).json()["id"]

    # 1. OPEN -> ASSIGNED
    res1 = client.patch(f"/api/v1/cases/{case_id}/status", json={"status": "ASSIGNED"})
    assert res1.status_code == 200
    assert res1.json()["status"] == "ASSIGNED"

    # 2. ASSIGNED -> UNDER_REVIEW
    res2 = client.patch(f"/api/v1/cases/{case_id}/status", json={"status": "UNDER_REVIEW"})
    assert res2.status_code == 200
    assert res2.json()["status"] == "UNDER_REVIEW"

    # 3. UNDER_REVIEW -> DECISION_PENDING
    res3 = client.patch(f"/api/v1/cases/{case_id}/status", json={"status": "DECISION_PENDING"})
    assert res3.status_code == 200
    assert res3.json()["status"] == "DECISION_PENDING"

    # 4. DECISION_PENDING -> CLOSED
    res4 = client.patch(f"/api/v1/cases/{case_id}/status", json={"status": "CLOSED", "reason": "Decision rendered"})
    assert res4.status_code == 200
    assert res4.json()["status"] == "CLOSED"
    assert res4.json()["closed_at"] is not None

    # Check that events were recorded for each transition
    events_res = client.get(f"/api/v1/cases/{case_id}/events")
    assert events_res.status_code == 200
    events = events_res.json()
    assert len(events) == 5  # 1 creation + 4 transitions

def test_assign_reviewer_to_case():
    db = SessionLocal()
    reviewer = db.query(Reviewer).filter(Reviewer.status == "ACTIVE").first()
    if not reviewer:
        reviewer = Reviewer(
            reviewer_code="REV-CASE-ASSIGN-0001",
            full_name="Case Assignment Reviewer",
            email="case.assignment.reviewer@example.com",
            department="Academic Integrity",
            max_active_cases=5,
            status="ACTIVE"
        )
        db.add(reviewer)
        db.commit()
        db.refresh(reviewer)
    reviewer_id = reviewer.id
    db.close()

    flag_id = create_sample_flag()
    payload = {
        "case_code": f"CASE-2026-50{flag_id:04d}",
        "flag_id": flag_id,
        "title": "Reviewer assignment test"
    }
    case_id = client.post("/api/v1/cases/", json=payload).json()["id"]

    assign_res = client.post(
        f"/api/v1/cases/{case_id}/assign",
        json={"reviewer_id": reviewer_id}
    )
    assert assign_res.status_code == 200
    assert assign_res.json()["status"] == "ASSIGNED"

    # Verify duplicate assignment rejected
    assign_res2 = client.post(
        f"/api/v1/cases/{case_id}/assign",
        json={"reviewer_id": reviewer.id}
    )
    assert assign_res2.status_code == 400
    assert "already has an active reviewer" in assign_res2.json()["detail"]

