from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.models.flag import Flag
from app.models.similarity_report import SimilarityReport
from app.models.submission import Submission
from app.database.connection import get_db
from app.routes.submission_routes import router
from app.services.submission_service import SubmissionService


def make_service(first_results):
    db = Mock()
    db.query.return_value.filter.return_value.first.side_effect = first_results
    return SubmissionService(db), db


def make_client(first_results):
    db = Mock()
    db.query.return_value.filter.return_value.first.side_effect = first_results
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: db
    return TestClient(app), db


def test_delete_unanalysed_submission():
    submission = SimpleNamespace(id=12)
    service, db = make_service([submission, None, None])

    assert service.delete_submission(12) is True

    db.delete.assert_called_once_with(submission)
    db.commit.assert_called_once()


def test_delete_submission_with_analysis_is_rejected():
    service, db = make_service([SimpleNamespace(id=12), (31,)])

    with pytest.raises(ValueError, match="after similarity analysis"):
        service.delete_submission(12)

    assert db.query.call_args_list[1].args == (SimilarityReport.id,)
    db.delete.assert_not_called()
    db.commit.assert_not_called()


def test_delete_submission_with_flag_is_rejected():
    service, db = make_service([SimpleNamespace(id=12), None, (42,)])

    with pytest.raises(ValueError, match="integrity flag or case"):
        service.delete_submission(12)

    assert db.query.call_args_list[2].args == (Flag.id,)
    db.delete.assert_not_called()
    db.commit.assert_not_called()


def test_delete_missing_submission_returns_false():
    service, db = make_service([None])

    assert service.delete_submission(999) is False

    db.delete.assert_not_called()
    db.commit.assert_not_called()


def test_delete_endpoint_returns_no_content_when_deletion_succeeds():
    client, db = make_client([SimpleNamespace(id=12), None, None])

    response = client.delete("/api/v1/submissions/12")

    assert response.status_code == 204
    db.commit.assert_called_once()


def test_delete_endpoint_returns_conflict_for_analyzed_submission():
    client, db = make_client([SimpleNamespace(id=12), (31,)])

    response = client.delete("/api/v1/submissions/12")

    assert response.status_code == 409
    assert "after similarity analysis" in response.json()["detail"]
    db.delete.assert_not_called()


def test_delete_endpoint_returns_not_found_for_missing_submission():
    client, db = make_client([None])

    response = client.delete("/api/v1/submissions/999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Submission not found"
