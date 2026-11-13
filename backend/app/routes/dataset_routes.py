import json
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse


router = APIRouter(prefix="/datasets", tags=["Synthetic Dataset"])
GENERATED_DATA_DIR = Path(__file__).resolve().parents[2] / "generated_data"

_CSV_EXPORTS = (
    "learners.csv",
    "assessments.csv",
    "reviewers.csv",
    "integrity_rules.csv",
    "submissions.csv",
    "similarity_reports.csv",
    "similarity_matches.csv",
    "flags.csv",
    "cases.csv",
    "case_flags.csv",
    "case_assignments.csv",
    "reviewer_conflicts.csv",
    "case_events.csv",
    "evidence_items.csv",
    "case_decisions.csv",
    "decision_evidence.csv",
    "appeals.csv",
    "appeal_evidence.csv",
    "appeal_events.csv",
)

_EXPORT_CATEGORIES = {
    **{filename: "input_data" for filename in _CSV_EXPORTS},
    "data.json": "input_data",
    "ground_truth.csv": "evaluation_labels",
    "ground_truth.json": "evaluation_labels",
    "seed.sql": "database_seed",
    "README.md": "documentation",
    "data_dictionary.json": "documentation",
    "source_manifest.json": "documentation",
    "validation_summary.json": "documentation",
}

_MEDIA_TYPES = {
    ".csv": "text/csv",
    ".json": "application/json",
    ".sql": "application/sql",
    ".md": "text/markdown",
}


@router.get("/generated")
def get_generated_dataset_info():
    summary_path = GENERATED_DATA_DIR / "validation_summary.json"
    summary = {}
    if summary_path.is_file():
        with summary_path.open(encoding="utf-8") as source:
            summary = json.load(source)

    files = []
    for filename, category in _EXPORT_CATEGORIES.items():
        export_path = GENERATED_DATA_DIR / filename
        if export_path.is_file():
            files.append({
                "filename": filename,
                "category": category,
                "size_bytes": export_path.stat().st_size,
            })

    return {
        "status": summary.get("status", "NOT_GENERATED"),
        "metrics": summary.get("metrics", {}),
        "row_counts": summary.get("row_counts", {}),
        "files": files,
    }


@router.get("/generated/files/{filename}")
def download_generated_dataset_file(filename: str):
    if filename not in _EXPORT_CATEGORIES:
        raise HTTPException(status_code=404, detail="Dataset export not found.")

    export_path = GENERATED_DATA_DIR / filename
    if not export_path.is_file():
        raise HTTPException(status_code=404, detail="Dataset export not found.")

    return FileResponse(
        path=export_path,
        filename=filename,
        media_type=_MEDIA_TYPES.get(export_path.suffix, "application/octet-stream"),
    )
