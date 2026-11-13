from app.models.submission_exercise import Submission

def test_submission_no_flag():
    s = Submission("SUB-001", 1, "Essay 1", 12.0)
    assert s.check_similarity() == "NO_FLAG"

def test_submission_review_required():
    s = Submission("SUB-002", 2, "Essay 2", 20.0)
    assert s.check_similarity() == "REVIEW_REQUIRED"
    s2 = Submission("SUB-003", 2, "Essay 3", 69.99)
    assert s2.check_similarity() == "REVIEW_REQUIRED"

def test_submission_priority_review():
    s = Submission("SUB-004", 3, "Final Project", 70.0)
    assert s.check_similarity() == "PRIORITY_REVIEW"
    s2 = Submission("SUB-005", 4, "Final Project", 85.0)
    assert s2.check_similarity() == "PRIORITY_REVIEW"

