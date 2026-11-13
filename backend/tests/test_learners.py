from fastapi.testclient import TestClient
from app.main import app
from app.database.connection import SessionLocal
from app.models import (
    Learner, Submission, SimilarityReport, SimilarityMatch, Flag,
    Case, CaseFlag, CaseAssignment, CaseEvent, ReviewerConflict,
    DecisionEvidence, CaseDecision, EvidenceItem,
)

client = TestClient(app)

def setup_function():
    """Clean tables in reverse dependency order before test run."""
    db = SessionLocal()
    # Phase 8 — newest tables first
    db.query(DecisionEvidence).delete()
    db.query(CaseDecision).delete()
    db.query(EvidenceItem).delete()
    # Phase 7
    db.query(ReviewerConflict).delete()
    # Phase 6
    db.query(CaseEvent).delete()
    db.query(CaseAssignment).delete()
    db.query(CaseFlag).delete()
    db.query(Case).delete()
    # Phase 5
    db.query(Flag).delete()
    db.query(SimilarityMatch).delete()
    db.query(SimilarityReport).delete()
    # Phase 4
    db.query(Submission).delete()
    # Phase 2
    db.query(Learner).delete()
    db.commit()
    db.close()

def test_create_learner_success():
    payload = {
        "learner_code": "LRN-2026-000001",
        "name": "Raju Bathini",
        "email": "raju@example.com",
        "department": "Computer Science"
    }
    response = client.post("/api/v1/learners/", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] is not None
    assert data["learner_code"] == payload["learner_code"]
    assert data["name"] == payload["name"]
    assert data["email"] == payload["email"]
    assert data["department"] == payload["department"]
    assert data["status"] == "ACTIVE"

def test_get_all_learners():
    payload = {
        "learner_code": "LRN-2026-000001",
        "name": "Raju Bathini",
        "email": "raju@example.com",
        "department": "Computer Science"
    }
    client.post("/api/v1/learners/", json=payload)
    response = client.get("/api/v1/learners/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["learner_code"] == payload["learner_code"]

def test_get_learner_by_id():
    payload = {
        "learner_code": "LRN-2026-000001",
        "name": "Raju Bathini",
        "email": "raju@example.com",
        "department": "Computer Science"
    }
    create_res = client.post("/api/v1/learners/", json=payload)
    created_id = create_res.json()["id"]

    response = client.get(f"/api/v1/learners/{created_id}")
    assert response.status_code == 200
    assert response.json()["id"] == created_id
    assert response.json()["name"] == "Raju Bathini"

def test_duplicate_email_conflict():
    payload1 = {
        "learner_code": "LRN-2026-000001",
        "name": "Raju Bathini",
        "email": "raju@example.com",
        "department": "Computer Science"
    }
    client.post("/api/v1/learners/", json=payload1)

    payload2 = {
        "learner_code": "LRN-2026-000002",
        "name": "Duplicate User",
        "email": "raju@example.com",
        "department": "Information Systems"
    }
    response = client.post("/api/v1/learners/", json=payload2)
    assert response.status_code == 409
    assert response.json()["detail"] == "Learner code or email already exists"

def test_learner_not_found():
    response = client.get("/api/v1/learners/999999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Learner not found"
