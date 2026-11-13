from fastapi.testclient import TestClient
from app.main import app
from app.database.connection import SessionLocal
from app.models import Learner, Assessment, Submission, SimilarityReport, SimilarityMatch, Flag
from app.services.similarity_service import SimilarityService
from app.services.analyzers.base_analyzer import SimilarityAnalyzer, AnalysisResult, MatchSource

client = TestClient(app)

# Custom Polymorphic Analyzer for testing high similarity
class CustomHighSimilarityAnalyzer(SimilarityAnalyzer):
    def analyze(self, submission_id: int, submission_code: str, file_reference: str | None = None) -> AnalysisResult:
        return AnalysisResult(
            overall_score=82.5,
            quotation_percentage=10.0,
            template_percentage=5.0,
            internet_percentage=67.5,
            matches=[
                MatchSource("QUOTATION", "Doc 1", 10.0, "Valid quotes"),
                MatchSource("INTERNET", "Online Code", 67.5, "External code match")
            ],
            engine_name="TestHighEngine",
            is_simulated=True
        )

# Custom Polymorphic Analyzer for testing low similarity
class CustomLowSimilarityAnalyzer(SimilarityAnalyzer):
    def analyze(self, submission_id: int, submission_code: str, file_reference: str | None = None) -> AnalysisResult:
        return AnalysisResult(
            overall_score=8.0,
            quotation_percentage=5.0,
            template_percentage=3.0,
            internet_percentage=0.0,
            matches=[
                MatchSource("QUOTATION", "Reference List", 5.0, "Bibliography"),
                MatchSource("TEMPLATE", "Class Header", 3.0, "Author tags")
            ],
            engine_name="TestLowEngine",
            is_simulated=True
        )

def get_or_create_submission():
    db = SessionLocal()
    learner = db.query(Learner).first()
    if not learner:
        learner = Learner(learner_code="LRN-SIM-01", name="Sim Learner", email="sim@example.com", department="CS")
        db.add(learner)
        db.commit()
        db.refresh(learner)

    assessment = db.query(Assessment).first()
    if not assessment:
        assessment = Assessment(assessment_code="ASM-SIM-01", title="Sim Assessment", assessment_type="ASSIGNMENT", max_marks=100)
        db.add(assessment)
        db.commit()
        db.refresh(assessment)

    submission = db.query(Submission).first()
    if not submission:
        submission = Submission(
            submission_code="SUB-2026-888001",
            learner_id=learner.id,
            assessment_id=assessment.id,
            version_number=1,
            status="SUBMITTED"
        )
        db.add(submission)
        db.commit()
        db.refresh(submission)

    sub_id = submission.id
    db.close()
    return sub_id

def test_polymorphic_high_similarity_creates_flag():
    sub_id = get_or_create_submission()
    db = SessionLocal()
    service = SimilarityService(db, analyzer=CustomHighSimilarityAnalyzer())
    result = service.analyze_submission(sub_id)
    db.close()

    assert result["report"] is not None
    assert result["report"].overall_score == 82.5
    assert result["rule_action"] == "PRIORITY_REVIEW"
    assert result["flag_created"] is True
    assert result["flag"] is not None
    assert result["flag"].flag_type == "PRIORITY_REVIEW"
    assert result["flag"].status == "OPEN"

def test_polymorphic_low_similarity_no_flag():
    sub_id = get_or_create_submission()
    db = SessionLocal()
    service = SimilarityService(db, analyzer=CustomLowSimilarityAnalyzer())
    result = service.analyze_submission(sub_id)
    db.close()

    assert result["report"].overall_score == 8.0
    assert result["rule_action"] == "INFORMATION"
    assert result["flag_created"] is False
    assert result["flag"] is None

def test_api_analyze_submission():
    sub_id = get_or_create_submission()
    response = client.post(f"/api/v1/similarity/analyze/{sub_id}")
    assert response.status_code == 200
    data = response.json()
    assert "report" in data
    assert "rule_action" in data
    assert "due_process_notice" in data
    assert len(data["report"]["matches"]) >= 1

def test_api_get_submission_reports():
    sub_id = get_or_create_submission()
    response = client.get(f"/api/v1/similarity/reports/submission/{sub_id}")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) >= 1

def test_api_get_flags():
    response = client.get("/api/v1/similarity/flags")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

