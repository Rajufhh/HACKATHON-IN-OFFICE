from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_get_assessments():
    seed_response = client.post("/api/v1/assessments/", json={
        "assessment_code": "ASM-2026-000001",
        "title": "Master Data Test Assessment",
        "assessment_type": "ASSIGNMENT",
        "max_marks": 100,
    })
    assert seed_response.status_code in (200, 409), seed_response.text

    response = client.get("/api/v1/assessments/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert any(a["assessment_code"] == "ASM-2026-000001" for a in data)

def test_create_assessment_and_get():
    payload = {
        "assessment_code": "ASM-TEST-0001",
        "title": "Algorithms & Complexity Exam",
        "description": "Comprehensive midterm examination",
        "assessment_type": "EXAM",
        "max_marks": 100,
        "status": "PUBLISHED"
    }
    create_res = client.post("/api/v1/assessments/", json=payload)
    assert create_res.status_code in [200, 409]
    if create_res.status_code == 200:
        created_id = create_res.json()["id"]
        get_res = client.get(f"/api/v1/assessments/{created_id}")
        assert get_res.status_code == 200
        assert get_res.json()["title"] == payload["title"]

def test_get_reviewers():
    seed_response = client.post("/api/v1/reviewers/", json={
        "reviewer_code": "REV-2026-000001",
        "full_name": "Master Data Test Reviewer",
        "email": "master-data-reviewer@example.com",
        "department": "Computer Science",
        "status": "ACTIVE",
    })
    assert seed_response.status_code in (200, 409), seed_response.text

    response = client.get("/api/v1/reviewers/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert any(r["reviewer_code"] == "REV-2026-000001" for r in data)

def test_create_reviewer_and_conflict():
    payload = {
        "reviewer_code": "REV-TEST-0001",
        "full_name": "Dr. Sarah Chen",
        "email": "sarah.chen@university.edu",
        "department": "Computer Science",
        "specialization": "Distributed Systems",
        "max_active_cases": 8,
        "status": "ACTIVE"
    }
    res1 = client.post("/api/v1/reviewers/", json=payload)
    if res1.status_code == 200:
        # Duplicate should return 409
        res2 = client.post("/api/v1/reviewers/", json=payload)
        assert res2.status_code == 409

def test_get_integrity_rules():
    rules = [
        {
            "rule_code": "RULE-MASTER-01",
            "rule_name": "Master Data Low Similarity",
            "min_similarity": 0,
            "max_similarity": 19,
            "action": "INFORMATION",
        },
        {
            "rule_code": "RULE-MASTER-02",
            "rule_name": "Master Data Minor Similarity",
            "min_similarity": 20,
            "max_similarity": 39,
            "action": "INFORMATION",
        },
        {
            "rule_code": "RULE-MASTER-03",
            "rule_name": "Master Data Review Required",
            "min_similarity": 40,
            "max_similarity": 69,
            "action": "REVIEW",
        },
        {
            "rule_code": "RULE-MASTER-04",
            "rule_name": "Master Data Priority Review",
            "min_similarity": 70,
            "max_similarity": 100,
            "action": "PRIORITY_REVIEW",
        },
    ]
    for rule in rules:
        seed_response = client.post("/api/v1/integrity-rules/", json=rule)
        assert seed_response.status_code in (200, 409), seed_response.text

    response = client.get("/api/v1/integrity-rules/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 4

def test_evaluate_similarity_scores():
    # Low score
    res_low = client.get("/api/v1/integrity-rules/evaluate/12.5")
    assert res_low.status_code == 200
    assert res_low.json()["recommended_action"] == "INFORMATION"

    # Moderate/high score
    res_mid = client.get("/api/v1/integrity-rules/evaluate/55.0")
    assert res_mid.status_code == 200
    assert res_mid.json()["recommended_action"] == "REVIEW"

    # Critical score
    res_high = client.get("/api/v1/integrity-rules/evaluate/85.0")
    assert res_high.status_code == 200
    assert res_high.json()["recommended_action"] == "PRIORITY_REVIEW"

