import csv
import json

from scripts.generate_synthetic_data import (
    generate_dataset,
    validate_dataset,
    verify_reproducibility,
    write_exports,
)


def _starter_dataset():
    return generate_dataset(
        submissions_count=1000,
        flags_count=100,
        cases_count=50,
        seed=20261022,
    )


def test_starter_dataset_reconciles_relationships_and_edge_cases():
    tables, ground_truth = _starter_dataset()
    summary = validate_dataset(tables, ground_truth, 1000, 100, 50)

    assert summary["status"] == "PASS_WITH_EXPECTED_ANOMALIES"
    assert summary["errors"] == []
    assert len(tables["submissions"]) == 1000
    assert len(tables["flags"]) == 100
    assert len(tables["cases"]) == 50
    assert tables["submissions"][0]["submission_code"] == "SUB-2026-000001"
    assert tables["similarity_reports"][0]["report_code"] == "SIM-000001-01"
    assert tables["integrity_rules"][0]["rule_code"] == "INT-2026-000001"
    assert tables["evidence_items"][0]["evidence_code"] == "EVD-000001-001"
    appeal = tables["appeals"][0]
    appeal_case_id = next(
        decision["case_id"]
        for decision in tables["case_decisions"]
        if decision["id"] == appeal["decision_id"]
    )
    assert appeal["appeal_code"] == f"APL-{appeal_case_id:06d}-01"
    assert summary["metrics"]["successful_appeal_count"] > 0
    assert summary["metrics"]["flagged_legitimate_overlap_count"] > 0
    assert summary["metrics"]["expected_anomaly_count"] == 4


def test_validator_rejects_invalid_enums_and_lifecycle_dates():
    tables, ground_truth = _starter_dataset()
    tables["similarity_reports"][0]["status"] = "GUILTY"
    tables["submissions"][0]["submitted_at"] = "2027-01-01 00:00:00"

    summary = validate_dataset(tables, ground_truth, 1000, 100, 50)

    assert any("similarity_reports.status" in error for error in summary["errors"])
    assert any("outside its assessment dates" in error for error in summary["errors"])


def test_fixed_seed_is_reproducible():
    result = verify_reproducibility(
        submissions_count=1000,
        flags_count=100,
        cases_count=50,
        seed=20261022,
    )

    assert result["reproducible"] is True
    assert result["first_sha256"] == result["second_sha256"]


def test_exports_keep_ground_truth_separate_and_include_seed_sql(tmp_path):
    tables, ground_truth = _starter_dataset()
    validation = validate_dataset(tables, ground_truth, 1000, 100, 50)

    manifest = write_exports(
        tmp_path,
        tables,
        ground_truth,
        validation,
        seed=20261022,
        parameters={"submissions": 1000, "flags": 100, "cases": 50},
    )

    exported_data = json.loads((tmp_path / "data.json").read_text(encoding="utf-8"))
    exported_truth = json.loads(
        (tmp_path / "ground_truth.json").read_text(encoding="utf-8")
    )
    with (tmp_path / "submissions.csv").open(
        encoding="utf-8", newline=""
    ) as source:
        submission_rows = list(csv.DictReader(source))

    assert set(exported_data["tables"]) == set(tables)
    assert "ground_truth" not in exported_data
    assert len(exported_truth) == len(ground_truth)
    assert len(submission_rows) == 1000
    assert "ground_truth" not in (tmp_path / "seed.sql").read_text(
        encoding="utf-8"
    ).lower()
    assert (tmp_path / "seed.sql").is_file()
    assert (tmp_path / "README.md").is_file()
    readme = (tmp_path / "README.md").read_text(encoding="utf-8")
    assert "three synthetic match components" in readme
    assert "four synthetic match components" not in readme
    assert (tmp_path / "data_dictionary.json").is_file()
    assert (tmp_path / "validation_summary.json").is_file()
    assert manifest["synthetic_only"] is True
    assert manifest["external_sources"] == []
    assert "ground_truth.csv" in manifest["checksums_sha256"]
