"""
Phase 8 Tests — Evidence Management & Human Decisions

Key scenario (the immutability proof):
  1. Create learner → assessment → submission → similarity analysis → flag
  2. Open a case, move it through OPEN → ASSIGNED → UNDER_REVIEW → DECISION_PENDING
  3. Add 3 evidence items to the case
  4. Record a decision referencing those 3 items
  5. Add a 4th evidence item AFTER the decision
  6. Prove the original decision snapshot still references exactly 3 items

Rejection tests:
  7. Decision rejected when case is NOT DECISION_PENDING
  8. Decision rejected when rationale is blank
  9. Decision rejected when reviewer has no CLEARED assignment
"""

from fastapi.testclient import TestClient
from app.main import app
from app.database.connection import SessionLocal
from app.models import (
    Learner, Assessment, Reviewer, IntegrityRule,
    Submission, SimilarityReport, SimilarityMatch, Flag,
    Case, CaseFlag, CaseAssignment, CaseEvent, ReviewerConflict,
    EvidenceItem, CaseDecision, DecisionEvidence,
)

client = TestClient(app)


# ---------------------------------------------------------------------------
# Shared state across tests in this module
# ---------------------------------------------------------------------------

class Ctx:
    """Simple namespace to hold IDs shared across tests."""
    learner_id: int = None
    assessment_id: int = None
    reviewer_id: int = None
    submission_id: int = None
    flag_id: int = None
    case_id: int = None
    second_case_id: int = None
    evidence_ids: list = []
    decision_id: int = None


ctx = Ctx()


# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

def setup_module(module):
    """
    Clean all test data in FK-safe reverse order, then ensure IntegrityRules
    exist so the similarity engine can create flags.

    Strategy: delete everything, then directly insert the 4 master rules
    via the ORM (bypassing the API to avoid duplicate-key errors).
    """
    db = SessionLocal()

    # Phase 8 — newest tables first
    db.query(DecisionEvidence).delete()
    db.query(CaseDecision).delete()
    db.query(EvidenceItem).delete()

    # Phase 7 / 6
    db.query(ReviewerConflict).delete()
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

    # Phase 3 master data
    db.query(Learner).delete()
    db.query(Assessment).delete()
    db.query(Reviewer).delete()
    db.query(IntegrityRule).delete()

    db.commit()

    # Re-seed the 4 integrity rules directly (the similarity engine needs them)
    rules = [
        IntegrityRule(rule_code="RULE-01", rule_name="Low Similarity",   min_similarity=0,  max_similarity=19,  action="INFORMATION",    description="Low similarity"),
        IntegrityRule(rule_code="RULE-02", rule_name="Minor Similarity",  min_similarity=20, max_similarity=39,  action="INFORMATION",    description="Minor similarity"),
        IntegrityRule(rule_code="RULE-03", rule_name="Review Required",   min_similarity=40, max_similarity=69,  action="REVIEW",         description="Review required"),
        IntegrityRule(rule_code="RULE-04", rule_name="Priority Review",   min_similarity=70, max_similarity=100, action="PRIORITY_REVIEW",description="Priority review"),
    ]
    for rule in rules:
        db.add(rule)
    db.commit()
    db.close()


# ---------------------------------------------------------------------------
# Prerequisite setup tests (must run in order — pytest runs them alphabetically
# but we prefix with numbers to enforce order)
# ---------------------------------------------------------------------------

def test_01_create_learner():
    r = client.post("/api/v1/learners/", json={
        "learner_code": "LRN-2026-P8-001",
        "name": "Phase8 Learner",
        "email": "p8learner@example.com",
        "department": "Computer Science",
    })
    assert r.status_code == 200, r.text
    ctx.learner_id = r.json()["id"]


def test_02_create_assessment():
    r = client.post("/api/v1/assessments/", json={
        "assessment_code": "ASS-2026-P8-001",
        "title": "Phase8 Assignment",
        "assessment_type": "ASSIGNMENT",
        "max_score": 100,
    })
    assert r.status_code == 200, r.text
    ctx.assessment_id = r.json()["id"]


def test_03_create_reviewer():
    r = client.post("/api/v1/reviewers/", json={
        "reviewer_code": "REV-2026-P8-001",
        "full_name": "Phase8 Reviewer",
        "email": "p8reviewer@example.com",
        "department": "Computer Science",
        "specialization": "Academic Integrity",
    })
    assert r.status_code == 200, r.text
    ctx.reviewer_id = r.json()["id"]


def test_04_create_submission_and_flag():
    """Create submission and run similarity analysis to generate a flag."""
    r = client.post("/api/v1/submissions/", json={
        "submission_code": "SUB-2026-800001",
        "learner_id": ctx.learner_id,
        "assessment_id": ctx.assessment_id,
        "version": 1,
        "status": "SUBMITTED",
        "content_hash": "deadbeef00000001",
    })
    assert r.status_code == 200, r.text
    ctx.submission_id = r.json()["id"]

    r = client.post(f"/api/v1/similarity/analyze/{ctx.submission_id}")
    assert r.status_code in (200, 201), r.text

    r = client.get("/api/v1/similarity/flags")
    assert r.status_code == 200, r.text
    flags = [f for f in r.json() if f["submission_id"] == ctx.submission_id]
    assert len(flags) >= 1, "Expected at least one flag after similarity analysis"
    ctx.flag_id = flags[0]["id"]


def test_05_open_case():
    r = client.post("/api/v1/cases/", json={
        "case_code": "CASE-2026-000001",
        "flag_id": ctx.flag_id,
        "title": "Phase 8 Test Case"
    })
    assert r.status_code == 201, r.text
    ctx.case_id = r.json()["id"]
    assert isinstance(ctx.case_id, int)
    assert r.json()["status"] == "OPEN"


def test_06_assign_reviewer():
    r = client.post(f"/api/v1/cases/{ctx.case_id}/assign", json={
        "reviewer_id": ctx.reviewer_id,
    })
    assert r.status_code == 200, r.text
    with SessionLocal() as db:
        assignment = db.query(CaseAssignment).filter_by(
            case_id=ctx.case_id,
            reviewer_id=ctx.reviewer_id,
            status="ACTIVE"
        ).one()
        assert assignment.conflict_status == "CLEARED"


def test_07_advance_to_decision_pending():
    r = client.patch(f"/api/v1/cases/{ctx.case_id}/status", json={"status": "UNDER_REVIEW"})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "UNDER_REVIEW"

    r = client.patch(f"/api/v1/cases/{ctx.case_id}/status", json={"status": "DECISION_PENDING"})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "DECISION_PENDING"


# ---------------------------------------------------------------------------
# Evidence tests
# ---------------------------------------------------------------------------

def test_08_add_three_evidence_items():
    ctx.evidence_ids = []
    items = [
        {
            "case_id": ctx.case_id,
            "evidence_type": "DOCUMENT",
            "title": "Turnitin Report PDF",
            "description": "Original similarity report from Turnitin",
            "source_reference": "turnitin://report/12345",
            "added_by": ctx.reviewer_id,
        },
        {
            "case_id": ctx.case_id,
            "evidence_type": "SUBMISSION_VERSION",
            "title": "Original Submission v1",
            "description": "First submitted version of the assignment",
            "added_by": ctx.reviewer_id,
        },
        {
            "case_id": ctx.case_id,
            "evidence_type": "EXPLANATION",
            "title": "Learner Written Explanation",
            "description": "Learner's written response to the similarity allegation",
            "added_by": ctx.reviewer_id,
        },
    ]
    for item in items:
        r = client.post("/api/v1/evidence/", json=item)
        assert r.status_code == 201, r.text
        data = r.json()
        assert data["evidence_code"].startswith("EVD-")
        ctx.evidence_ids.append(data["id"])

    assert len(ctx.evidence_ids) == 3


def test_09_list_evidence_for_case():
    r = client.get(f"/api/v1/evidence/case/{ctx.case_id}")
    assert r.status_code == 200, r.text
    items = r.json()
    assert len(items) == 3
    for item in items:
        assert item["case_id"] == ctx.case_id


def test_10_reject_evidence_with_invalid_type():
    r = client.post("/api/v1/evidence/", json={
        "case_id": ctx.case_id,
        "evidence_type": "PHOTO",   # not in ALLOWED_EVIDENCE_TYPES
        "title": "Invalid type test",
    })
    assert r.status_code == 422, r.text


# ---------------------------------------------------------------------------
# Decision tests
# ---------------------------------------------------------------------------

def test_11_record_decision_with_three_evidence_items():
    """
    THE IMMUTABILITY PROOF — Part 1: record decision referencing 3 evidence items.
    """
    r = client.post("/api/v1/decisions/", json={
        "case_id": ctx.case_id,
        "reviewer_id": ctx.reviewer_id,
        "outcome": "BREACH_ESTABLISHED",
        "rationale": (
            "The learner's submitted work shows a 75% similarity score with "
            "another student's submission. The learner's written explanation "
            "did not satisfactorily account for the matching content. "
            "Based on the three evidence items reviewed, a breach is established."
        ),
        "evidence_ids": ctx.evidence_ids,
    })
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["outcome"] == "BREACH_ESTABLISHED"
    assert data["decision_code"].startswith("DEC-")
    ctx.decision_id = data["id"]


def test_12_add_fourth_evidence_after_decision():
    """
    THE IMMUTABILITY PROOF — Part 2: add a 4th evidence item AFTER the decision.
    """
    r = client.post("/api/v1/evidence/", json={
        "case_id": ctx.case_id,
        "evidence_type": "OTHER",
        "title": "Late-arriving Evidence (4th item)",
        "description": "Added AFTER the decision — must NOT appear in the original snapshot.",
        "added_by": ctx.reviewer_id,
    })
    assert r.status_code == 201, r.text

    r = client.get(f"/api/v1/evidence/case/{ctx.case_id}")
    assert r.status_code == 200
    assert len(r.json()) == 4   # now 4 total


def test_13_decision_snapshot_still_has_exactly_three_items():
    """
    THE IMMUTABILITY PROOF — Part 3: snapshot must still show exactly 3, not 4.
    """
    r = client.get(f"/api/v1/decisions/{ctx.decision_id}")
    assert r.status_code == 200, r.text
    data = r.json()

    snapshot = data["evidence_snapshot"]
    assert len(snapshot) == 3, (
        f"Expected 3 items in decision snapshot, got {len(snapshot)}. "
        "Late evidence must NOT retroactively appear in the snapshot."
    )

    snapshot_codes = {s["evidence_code_snapshot"] for s in snapshot}
    assert len(snapshot_codes) == 3
    for s in snapshot:
        assert s["evidence_title_snapshot"]
        assert s["evidence_type_snapshot"]


# ---------------------------------------------------------------------------
# Rejection tests
# ---------------------------------------------------------------------------

def test_14_reject_decision_when_case_not_decision_pending():
    """Decision on an OPEN case (not DECISION_PENDING) must be rejected."""
    r = client.post("/api/v1/learners/", json={
        "learner_code": "LRN-2026-P8-002",
        "name": "Second Learner",
        "email": "second@example.com",
        "department": "Mathematics",
    })
    assert r.status_code == 200
    second_learner_id = r.json()["id"]

    r = client.post("/api/v1/submissions/", json={
        "submission_code": "SUB-2026-800003",
        "learner_id": second_learner_id,
        "assessment_id": ctx.assessment_id,
        "version": 1,
        "status": "SUBMITTED",
        "content_hash": "deadbeef00000002",
    })
    assert r.status_code == 200
    sub_id = r.json()["id"]

    r = client.post(f"/api/v1/similarity/analyze/{sub_id}")
    assert r.status_code in (200, 201)

    r = client.get("/api/v1/similarity/flags")
    flags = [f for f in r.json() if f["submission_id"] == sub_id]
    assert len(flags) >= 1
    second_flag_id = flags[0]["id"]

    case_response = client.post("/api/v1/cases/", json={
        "case_code": "CASE-2026-000002",
        "flag_id": second_flag_id,
        "title": "Phase 8 Rejection Test Case"
    })
    assert case_response.status_code == 201, case_response.text
    ctx.second_case_id = case_response.json()["id"]
    # Case is OPEN — NOT DECISION_PENDING

    r = client.post("/api/v1/decisions/", json={
        "case_id": ctx.second_case_id,
        "reviewer_id": ctx.reviewer_id,
        "outcome": "NO_BREACH",
        "rationale": "Should not reach this — case is OPEN not DECISION_PENDING",
        "evidence_ids": [],
    })
    assert r.status_code == 422, f"Expected 422, got {r.status_code}: {r.text}"
    assert "DECISION_PENDING" in r.json()["detail"]


def test_15_reject_decision_with_blank_rationale():
    """Decision with whitespace-only rationale must be rejected (service strips it)."""
    r = client.post("/api/v1/decisions/", json={
        "case_id": ctx.case_id,
        "reviewer_id": ctx.reviewer_id,
        "outcome": "NO_BREACH",
        "rationale": "   ",
        "evidence_ids": [],
    })
    assert r.status_code == 422, f"Expected 422, got {r.status_code}: {r.text}"


def test_16_reject_decision_with_no_cleared_assignment():
    """Reviewer with no CLEARED assignment to the case must be rejected."""
    r = client.post("/api/v1/reviewers/", json={
        "reviewer_code": "REV-2026-P8-002",
        "full_name": "Unassigned Reviewer",
        "email": "unassigned@example.com",
        "department": "Biology",
        "specialization": "Academic Integrity",
    })
    assert r.status_code == 200
    unassigned_reviewer_id = r.json()["id"]

    r = client.post("/api/v1/decisions/", json={
        "case_id": ctx.case_id,
        "reviewer_id": unassigned_reviewer_id,
        "outcome": "NO_BREACH",
        "rationale": "This reviewer was never assigned — must be rejected.",
        "evidence_ids": [],
    })
    assert r.status_code == 422, f"Expected 422, got {r.status_code}: {r.text}"
    detail = r.json()["detail"].lower()
    assert "cleared" in detail or "assignment" in detail


def test_17_get_evidence_by_id():
    eid = ctx.evidence_ids[0]
    r = client.get(f"/api/v1/evidence/{eid}")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["id"] == eid
    assert data["case_id"] == ctx.case_id


def test_18_list_case_decisions():
    r = client.get(f"/api/v1/decisions/case/{ctx.case_id}")
    assert r.status_code == 200, r.text
    decisions = r.json()
    assert len(decisions) >= 1
    assert decisions[0]["outcome"] == "BREACH_ESTABLISHED"


def test_19_evidence_404_for_missing_id():
    r = client.get("/api/v1/evidence/999999")
    assert r.status_code == 404, r.text


def test_20_decision_404_for_missing_id():
    r = client.get("/api/v1/decisions/999999")
    assert r.status_code == 404, r.text
