import json

import pytest
from fastapi import HTTPException

from app.routes import dataset_routes


def test_generated_dataset_lists_input_and_separate_evaluation_files(tmp_path, monkeypatch):
    monkeypatch.setattr(dataset_routes, "GENERATED_DATA_DIR", tmp_path)
    (tmp_path / "validation_summary.json").write_text(
        json.dumps({
            "status": "PASS_WITH_EXPECTED_ANOMALIES",
            "row_counts": {"submissions": 10},
            "metrics": {"successful_appeal_count": 1},
        }),
        encoding="utf-8",
    )
    (tmp_path / "data.json").write_text("{}", encoding="utf-8")
    (tmp_path / "ground_truth.json").write_text("not parsed by the listing route", encoding="utf-8")

    result = dataset_routes.get_generated_dataset_info()

    assert result["status"] == "PASS_WITH_EXPECTED_ANOMALIES"
    assert result["row_counts"] == {"submissions": 10}
    files = {item["filename"]: item for item in result["files"]}
    assert files["data.json"]["category"] == "input_data"
    assert files["ground_truth.json"]["category"] == "evaluation_labels"


def test_download_only_serves_allowlisted_generated_files(tmp_path, monkeypatch):
    monkeypatch.setattr(dataset_routes, "GENERATED_DATA_DIR", tmp_path)
    export = tmp_path / "data.json"
    export.write_text("{}", encoding="utf-8")

    response = dataset_routes.download_generated_dataset_file("data.json")

    assert response.path == export
    with pytest.raises(HTTPException) as error:
        dataset_routes.download_generated_dataset_file("..\\private.env")
    assert error.value.status_code == 404


def test_download_returns_not_found_when_allowlisted_file_is_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(dataset_routes, "GENERATED_DATA_DIR", tmp_path)

    with pytest.raises(HTTPException) as error:
        dataset_routes.download_generated_dataset_file("data.json")

    assert error.value.status_code == 404
