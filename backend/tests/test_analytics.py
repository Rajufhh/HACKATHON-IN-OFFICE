from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_analytics_overview_shape():
    response = client.get("/api/v1/analytics/overview")

    assert response.status_code == 200, response.text
    data = response.json()

    assert set(data) == {
        "metrics",
        "case_status",
        "flag_status",
        "decision_outcomes",
        "appeal_status",
        "appeal_outcomes",
    }
    assert set(data["metrics"]) == {
        "total_learners",
        "total_assessments",
        "total_submissions",
        "total_flags",
        "total_cases",
        "total_reviewers",
        "total_decisions",
        "total_appeals",
    }
    assert all(
        isinstance(count, int) and count >= 0
        for count in data["metrics"].values()
    )

    for distribution_name in (
        "case_status",
        "flag_status",
        "decision_outcomes",
        "appeal_status",
        "appeal_outcomes",
    ):
        distribution = data[distribution_name]
        assert isinstance(distribution, list)
        assert all(
            set(item) == {"label", "count"}
            and isinstance(item["label"], str)
            and isinstance(item["count"], int)
            and item["count"] >= 0
            for item in distribution
        )
