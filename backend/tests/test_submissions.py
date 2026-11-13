from fastapi.testclient import TestClient
from app.main import app
from app.database.connection import SessionLocal
from app.models import Learner, Assessment, Submission

client = TestClient(app)

def get_or_create_parent_ids():
    db = SessionLocal()
    learner = db.query(Learner).first()
    if not learner:
        learner = Learner(
            learner_code="LRN-2026-999001",
            name="Test Learner",
            email="test.learner.sub@example.com",
            department="Computer Science"
        )
        db.add(learner)
        db.commit()
        db.refresh(learner)

    assessment = db.query(Assessment).first()
    if not assessment:
        assessment = Assessment(
            assessment_code="ASM-2026-999001",
            title="Test Assessment",
            assessment_type="ASSIGNMENT",
            max_marks=100
        )
        db.add(assessment)
        db.commit()
        db.refresh(assessment)

    l_id, a_id = learner.id, assessment.id
    db.close()
    return l_id, a_id

def test_create_submission_success():
    learner_id, assessment_id = get_or_create_parent_ids()

    payload = {
        "submission_code": "SUB-2026-000001",
        "learner_id": learner_id,
        "assessment_id": assessment_id,
        "file_reference": "uploads/python_assignment.pdf",
        "content_hash": "sample_sha256_hash",
        "version_number": 1
    }

    response = client.post("/api/v1/submissions/", json=payload)
    assert response.status_code in [200, 409]
    if response.status_code == 200:
        data = response.json()
        assert data["submission_code"] == payload["submission_code"]
        assert data["learner_id"] == learner_id
        assert data["assessment_id"] == assessment_id
        assert data["version_number"] == 1
        assert data["status"] == "SUBMITTED"
        assert "submitted_at" in data

def test_get_submissions():
    response = client.get("/api/v1/submissions/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_get_submission_by_id():
    learner_id, assessment_id = get_or_create_parent_ids()
    payload = {
        "submission_code": "SUB-2026-000002",
        "learner_id": learner_id,
        "assessment_id": assessment_id,
        "version_number": 1
    }
    create_res = client.post("/api/v1/submissions/", json=payload)
    if create_res.status_code == 200:
        sub_id = create_res.json()["id"]
        get_res = client.get(f"/api/v1/submissions/{sub_id}")
        assert get_res.status_code == 200
        assert get_res.json()["submission_code"] == payload["submission_code"]

def test_get_submissions_by_learner():
    learner_id, _ = get_or_create_parent_ids()
    response = client.get(f"/api/v1/submissions/learner/{learner_id}")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_create_submission_invalid_learner():
    _, assessment_id = get_or_create_parent_ids()
    payload = {
        "submission_code": "SUB-2026-999999",
        "learner_id": 999999,  # Non-existent learner
        "assessment_id": assessment_id,
        "version_number": 1
    }
    response = client.post("/api/v1/submissions/", json=payload)
    assert response.status_code == 404
    assert response.json()["detail"] == "Learner does not exist"

def test_create_submission_invalid_assessment():
    learner_id, _ = get_or_create_parent_ids()
    payload = {
        "submission_code": "SUB-2026-999998",
        "learner_id": learner_id,
        "assessment_id": 999999,  # Non-existent assessment
        "version_number": 1
    }
    response = client.post("/api/v1/submissions/", json=payload)
    assert response.status_code == 404
    assert response.json()["detail"] == "Assessment does not exist"

def test_create_submission_invalid_code_pattern():
    learner_id, assessment_id = get_or_create_parent_ids()
    payload = {
        "submission_code": "INVALID-FORMAT",
        "learner_id": learner_id,
        "assessment_id": assessment_id,
        "version_number": 1
    }
    response = client.post("/api/v1/submissions/", json=payload)
    assert response.status_code == 422  # Pydantic validation error

def test_submission_version_constraint():
    learner_id, assessment_id = get_or_create_parent_ids()
    payload = {
        "submission_code": "SUB-2026-000003",
        "learner_id": learner_id,
        "assessment_id": assessment_id,
        "version_number": 0  # Invalid per Field(ge=1)
    }
    response = client.post("/api/v1/submissions/", json=payload)
    assert response.status_code == 422

