from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import sys
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


GENERATOR_VERSION = "1.0.0"
DEFAULT_SEED = 20261022
DEFAULT_OUTPUT = Path(__file__).resolve().parents[1] / "generated_data"

TABLE_COLUMNS: dict[str, list[str]] = {
    "learners": [
        "id", "learner_code", "name", "email", "department", "status",
    ],
    "assessments": [
        "id", "assessment_code", "title", "description", "assessment_type",
        "max_marks", "due_date", "status", "created_at",
    ],
    "reviewers": [
        "id", "reviewer_code", "full_name", "email", "department",
        "specialization", "max_active_cases", "status", "created_at",
    ],
    "integrity_rules": [
        "id", "rule_code", "rule_name", "min_similarity", "max_similarity",
        "action", "description", "created_at",
    ],
    "submissions": [
        "id", "submission_code", "learner_id", "assessment_id",
        "submitted_at", "file_reference", "content_hash", "version_number",
        "status",
    ],
    "similarity_reports": [
        "id", "report_code", "submission_id", "overall_score",
        "quotation_percentage", "template_percentage", "internet_percentage",
        "analyzed_at", "status",
    ],
    "similarity_matches": [
        "id", "report_id", "source_type", "source_reference",
        "matched_percentage", "description",
    ],
    "flags": [
        "id", "flag_code", "submission_id", "report_id",
        "integrity_rule_id", "flag_type", "status", "reason", "created_at",
    ],
    "cases": [
        "id", "case_code", "learner_id", "title", "description", "status",
        "priority", "opened_at", "closed_at",
    ],
    "case_flags": ["id", "case_id", "flag_id"],
    "case_assignments": [
        "id", "case_id", "reviewer_id", "conflict_status", "assigned_at",
        "unassigned_at", "status",
    ],
    "reviewer_conflicts": [
        "id", "reviewer_id", "case_id", "conflict_type", "reason", "status",
        "declared_at", "reviewed_at", "reviewed_by", "review_notes",
    ],
    "case_events": [
        "id", "case_id", "event_type", "description", "actor_id",
        "actor_role", "created_at",
    ],
    "evidence_items": [
        "id", "evidence_code", "case_id", "evidence_type", "title",
        "description", "source_reference", "sha256_hash", "mime_type",
        "file_size_bytes", "collected_at", "added_at", "added_by",
    ],
    "case_decisions": [
        "id", "decision_code", "case_id", "reviewer_id", "outcome",
        "rationale", "decided_at",
    ],
    "decision_evidence": [
        "id", "decision_id", "evidence_id", "evidence_code_snapshot",
        "evidence_title_snapshot", "evidence_type_snapshot",
    ],
    "appeals": [
        "id", "appeal_code", "decision_id", "learner_id",
        "assigned_reviewer_id", "grounds", "status", "outcome",
        "outcome_rationale", "submitted_at", "assigned_at", "resolved_at",
    ],
    "appeal_evidence": [
        "id", "appeal_id", "evidence_id", "evidence_code_snapshot",
        "evidence_title_snapshot", "evidence_type_snapshot", "added_by",
        "added_at",
    ],
    "appeal_events": [
        "id", "appeal_id", "event_type", "description", "actor_id",
        "actor_role", "created_at",
    ],
}

SQL_TABLE_ORDER = [
    "learners",
    "assessments",
    "reviewers",
    "integrity_rules",
    "submissions",
    "similarity_reports",
    "similarity_matches",
    "flags",
    "cases",
    "case_flags",
    "case_assignments",
    "reviewer_conflicts",
    "evidence_items",
    "case_decisions",
    "decision_evidence",
    "case_events",
    "appeals",
    "appeal_evidence",
    "appeal_events",
]

RULES = [
    (1, "INT-2026-000001", "Informational similarity", 0, 19, "INFORMATION"),
    (2, "INT-2026-000002", "Low similarity", 20, 39, "INFORMATION"),
    (3, "INT-2026-000003", "Review required", 40, 69, "REVIEW"),
    (4, "INT-2026-000004", "Priority review", 70, 100, "PRIORITY_REVIEW"),
]

SOURCES = ("QUOTATION", "TEMPLATE", "INTERNET")
SOURCE_PROFILES = {
    0: (0.65, 0.10, 0.25),
    1: (0.08, 0.65, 0.27),
    2: (0.18, 0.18, 0.64),
    3: (0.05, 0.05, 0.90),
}

GROUND_TRUTH_COLUMNS = [
    "record_type", "record_id", "submission_id", "case_id", "truth_label",
    "expected_review_action", "expected_decision", "actual_decision",
    "issue_type", "expected_behavior", "actual_behavior",
]


def _iso(value: datetime | None) -> str | None:
    return value.isoformat(sep=" ", timespec="seconds") if value else None


def _new_row(table: str, **values: Any) -> dict[str, Any]:
    expected = TABLE_COLUMNS[table]
    missing = set(expected) - values.keys()
    extra = values.keys() - set(expected)
    if missing or extra:
        raise ValueError(f"{table} columns mismatch; missing={missing}, extra={extra}")
    return {column: values[column] for column in expected}


def _truth_label(score: int, percentages: dict[str, float]) -> str:
    if score == 0:
        return "NO_MATCH"
    legitimate_share = percentages["QUOTATION"] + percentages["TEMPLATE"]
    return (
        "LEGITIMATE_OVERLAP"
        if legitimate_share >= score * 0.60
        else "POTENTIAL_UNAUTHORIZED_OVERLAP"
    )


def _expected_decision(truth_label: str, score: int) -> str:
    if truth_label in {"NO_MATCH", "LEGITIMATE_OVERLAP"}:
        return "NO_BREACH"
    if score >= 60:
        return "BREACH_ESTABLISHED"
    return "INSUFFICIENT_EVIDENCE"


def _score_for_submission(
    submission_id: int,
    flagged_ids: set[int],
    rng: random.Random,
) -> int:
    if submission_id not in flagged_ids:
        return rng.randint(0, 39)
    if rng.random() < 0.25:
        return rng.randint(70, 98)
    return rng.randint(40, 69)


def generate_dataset(
    submissions_count: int = 10_000,
    flags_count: int = 1_000,
    cases_count: int = 300,
    seed: int = DEFAULT_SEED,
) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]]]:
    """Create linked, deterministic synthetic records without database access."""
    if submissions_count < 10:
        raise ValueError("submissions_count must be at least 10.")
    if not 4 <= cases_count <= flags_count <= submissions_count:
        raise ValueError(
            "Counts must satisfy 4 <= cases_count <= flags_count <= submissions_count."
        )

    rng = random.Random(seed)
    tables: dict[str, list[dict[str, Any]]] = {
        table: [] for table in TABLE_COLUMNS
    }
    truth: list[dict[str, Any]] = []
    truth_by_submission: dict[int, dict[str, Any]] = {}
    case_by_submission: dict[int, int] = {}
    base_time = datetime(2026, 1, 1, 9, 0, 0)

    learner_count = max(100, (submissions_count + 3) // 4)
    assessment_count = max(10, min(50, (submissions_count + 399) // 400))
    reviewer_count = 30
    active_reviewer_ids = list(range(1, 25))
    inactive_statuses = ["ON_LEAVE"] * 4 + ["INACTIVE"] * 2

    for learner_id in range(1, learner_count + 1):
        tables["learners"].append(_new_row(
            "learners",
            id=learner_id,
            learner_code=f"LRN-2026-{learner_id:06d}",
            name=f"Synthetic Learner {learner_id:06d}",
            email=f"learner-{learner_id:06d}@example.invalid",
            department=("Computer Science", "Mathematics", "Engineering")[
                (learner_id - 1) % 3
            ],
            status="ACTIVE",
        ))

    for assessment_id in range(1, assessment_count + 1):
        created_at = base_time - timedelta(days=30) + timedelta(days=assessment_id)
        tables["assessments"].append(_new_row(
            "assessments",
            id=assessment_id,
            assessment_code=f"ASM-2026-{assessment_id:06d}",
            title=f"Synthetic Assessment {assessment_id:03d}",
            description="Synthetic assessment; no real course materials used.",
            assessment_type=("ASSIGNMENT", "PROJECT", "EXAM")[
                (assessment_id - 1) % 3
            ],
            max_marks=100,
            due_date=_iso(created_at + timedelta(days=210)),
            status="PUBLISHED",
            created_at=_iso(created_at),
        ))

    for reviewer_id in range(1, reviewer_count + 1):
        status = "ACTIVE" if reviewer_id <= 24 else inactive_statuses[reviewer_id - 25]
        tables["reviewers"].append(_new_row(
            "reviewers",
            id=reviewer_id,
            reviewer_code=f"REV-2026-{reviewer_id:06d}",
            full_name=f"Synthetic Reviewer {reviewer_id:03d}",
            email=f"reviewer-{reviewer_id:03d}@example.invalid",
            department=("Computer Science", "Mathematics", "Engineering")[
                (reviewer_id - 1) % 3
            ],
            specialization=("Similarity review", "Evidence review", "Appeals")[
                (reviewer_id - 1) % 3
            ],
            max_active_cases=25 if reviewer_id <= 24 else 10,
            status=status,
            created_at=_iso(base_time - timedelta(days=90) + timedelta(days=reviewer_id)),
        ))

    for rule_id, code, name, minimum, maximum, action in RULES:
        tables["integrity_rules"].append(_new_row(
            "integrity_rules",
            id=rule_id,
            rule_code=code,
            rule_name=name,
            min_similarity=minimum,
            max_similarity=maximum,
            action=action,
            description=(
                f"Scores {minimum}-{maximum} trigger {action}; a flag requests "
                "human review and never establishes misconduct."
            ),
            created_at=_iso(base_time - timedelta(days=365) + timedelta(days=rule_id)),
        ))

    flagged_ids = set(rng.sample(range(1, submissions_count + 1), flags_count))
    score_by_submission: dict[int, int] = {}
    for submission_id in range(1, submissions_count + 1):
        learner_id = (submission_id - 1) % learner_count + 1
        assessment_id = (submission_id - 1) % assessment_count + 1
        submitted_at = base_time + timedelta(
            days=(submission_id * 7) % 180,
            minutes=submission_id % 1440,
        )
        submission_code = f"SUB-2026-{submission_id:06d}"
        score = _score_for_submission(submission_id, flagged_ids, rng)
        score_by_submission[submission_id] = score

        tables["submissions"].append(_new_row(
            "submissions",
            id=submission_id,
            submission_code=submission_code,
            learner_id=learner_id,
            assessment_id=assessment_id,
            submitted_at=_iso(submitted_at),
            file_reference=f"synthetic://submissions/{submission_code}",
            content_hash=hashlib.sha256(
                f"{seed}:{submission_code}:synthetic".encode("utf-8")
            ).hexdigest(),
            version_number=1,
            status="SUBMITTED",
        ))

        profile = SOURCE_PROFILES[submission_id % len(SOURCE_PROFILES)]
        raw_parts = {
            "QUOTATION": round(score * profile[0], 2),
            "TEMPLATE": round(score * profile[1], 2),
            "INTERNET": round(score * profile[2], 2),
        }
        raw_parts["INTERNET"] = round(
            score - raw_parts["QUOTATION"] - raw_parts["TEMPLATE"],
            2,
        )
        report_id = submission_id
        analyzed_at = submitted_at + timedelta(minutes=5)
        tables["similarity_reports"].append(_new_row(
            "similarity_reports",
            id=report_id,
            report_code=f"SIM-{submission_id:06d}-01",
            submission_id=submission_id,
            overall_score=score,
            quotation_percentage=raw_parts["QUOTATION"],
            template_percentage=raw_parts["TEMPLATE"],
            internet_percentage=raw_parts["INTERNET"],
            analyzed_at=_iso(analyzed_at),
            status="COMPLETED",
        ))

        for source_index, source_type in enumerate(SOURCES):
            percentage = raw_parts[source_type]
            tables["similarity_matches"].append(_new_row(
                "similarity_matches",
                id=len(tables["similarity_matches"]) + 1,
                report_id=report_id,
                source_type=source_type,
                source_reference=(
                    f"synthetic://{source_type.lower()}/"
                    f"{submission_id:06d}/{source_index + 1:02d}"
                ),
                matched_percentage=percentage,
                description=(
                    f"Synthetic {source_type.lower()} component; "
                    "not derived from real learner work."
                ),
            ))

        truth_label = _truth_label(score, raw_parts)
        expected_decision = _expected_decision(truth_label, score)
        truth_row = {
            "record_type": "SUBMISSION",
            "record_id": submission_id,
            "submission_id": submission_id,
            "case_id": None,
            "truth_label": truth_label,
            "expected_review_action": (
                "INFORMATION" if score < 40
                else "REVIEW" if score < 70
                else "PRIORITY_REVIEW"
            ),
            "expected_decision": expected_decision,
            "actual_decision": None,
            "issue_type": None,
            "expected_behavior": (
                "No automatic guilt; route scores of 40 or greater to human review."
            ),
            "actual_behavior": None,
        }
        truth.append(truth_row)
        truth_by_submission[submission_id] = truth_row

    rule_for_score = {
        score: rule_id
        for rule_id, _, _, minimum, maximum, _ in RULES
        for score in range(minimum, maximum + 1)
    }
    flag_id_by_submission: dict[int, int] = {}
    for submission_id in sorted(flagged_ids):
        score = score_by_submission[submission_id]
        flag_id = len(tables["flags"]) + 1
        flag_id_by_submission[submission_id] = flag_id
        action = "REVIEW" if score < 70 else "PRIORITY_REVIEW"
        report_id = submission_id
        tables["flags"].append(_new_row(
            "flags",
            id=flag_id,
            flag_code=f"FLG-2026-{flag_id:06d}",
            submission_id=submission_id,
            report_id=report_id,
            integrity_rule_id=rule_for_score[score],
            flag_type=action,
            status="OPEN",
            reason=(
                f"Synthetic score {score} triggers {action}; human review required."
            ),
            created_at=tables["similarity_reports"][report_id - 1]["analyzed_at"],
        ))

    case_submission_ids = rng.sample(sorted(flagged_ids), cases_count)
    if case_submission_ids:
        first_case_submission = min(
            case_submission_ids,
            key=lambda item: (item % 4 not in {0, 1}, item),
        )
        case_submission_ids = [
            first_case_submission,
            *(sid for sid in case_submission_ids if sid != first_case_submission),
        ]
        if len(case_submission_ids) < cases_count:
            selected = set(case_submission_ids)
            case_submission_ids.extend(
                sid for sid in sorted(flagged_ids)
                if sid not in selected
            )
            case_submission_ids = case_submission_ids[:cases_count]
    auto_guilt_case_id = 1
    conflict_case_id = 2
    late_evidence_case_id = 3
    appeal_without_reviewer_case_id = 4
    case_id_by_submission = {
        submission_id: case_id
        for case_id, submission_id in enumerate(case_submission_ids, start=1)
    }
    case_time_by_id: dict[int, datetime] = {}
    reviewer_by_case: dict[int, int] = {}
    decision_by_case: dict[int, dict[str, Any]] = {}
    evidence_ids_by_case: dict[int, list[int]] = {}
    flagged_for_conflict: dict[int, int] = {}

    for case_id, submission_id in enumerate(case_submission_ids, start=1):
        case_by_submission[submission_id] = case_id
        truth_by_submission[submission_id]["case_id"] = case_id
        opened_at = datetime.fromisoformat(
            tables["similarity_reports"][submission_id - 1]["analyzed_at"]
        ) + timedelta(days=1, minutes=case_id)
        case_time_by_id[case_id] = opened_at
        learner_id = tables["submissions"][submission_id - 1]["learner_id"]
        tables["cases"].append(_new_row(
            "cases",
            id=case_id,
            case_code=f"CASE-2026-{case_id:06d}",
            learner_id=learner_id,
            title=f"Synthetic integrity review {case_id:06d}",
            description=(
                "Human review requested from a synthetic similarity signal; "
                "the signal is not a misconduct finding."
            ),
            status="CLOSED",
            priority="HIGH" if score_by_submission[submission_id] >= 70 else "NORMAL",
            opened_at=_iso(opened_at),
            closed_at=None,
        ))
        flag_id = flag_id_by_submission[submission_id]
        tables["case_flags"].append(_new_row(
            "case_flags",
            id=case_id,
            case_id=case_id,
            flag_id=flag_id,
        ))

        case_reviewer_id = active_reviewer_ids[(case_id - 1) % len(active_reviewer_ids)]
        if case_id == conflict_case_id:
            case_reviewer_id = active_reviewer_ids[8]
        reviewer_by_case[case_id] = case_reviewer_id
        conflict_status = "CONFLICT_DETECTED" if case_id == conflict_case_id else "CLEARED"
        assigned_at = opened_at + timedelta(minutes=15)
        decision_at = opened_at + timedelta(hours=4)
        closed_at = decision_at + timedelta(hours=1)
        tables["cases"][-1]["closed_at"] = _iso(closed_at)
        tables["case_assignments"].append(_new_row(
            "case_assignments",
            id=case_id,
            case_id=case_id,
            reviewer_id=case_reviewer_id,
            conflict_status=conflict_status,
            assigned_at=_iso(assigned_at),
            unassigned_at=_iso(closed_at),
            status="COMPLETED",
        ))

        if case_id % 10 == 0 or case_id == conflict_case_id:
            conflict_reviewer_id = (
                case_reviewer_id if case_id == conflict_case_id
                else active_reviewer_ids[(case_reviewer_id + 4) % len(active_reviewer_ids)]
            )
            status = "PENDING" if case_id % 20 == 0 else "CONFIRMED"
            tables["reviewer_conflicts"].append(_new_row(
                "reviewer_conflicts",
                id=len(tables["reviewer_conflicts"]) + 1,
                reviewer_id=conflict_reviewer_id,
                case_id=case_id,
                conflict_type="ACADEMIC" if case_id == conflict_case_id else "PROFESSIONAL",
                reason="Synthetic disclosed conflict; no real relationship is represented.",
                status="PENDING" if case_id == conflict_case_id else status,
                declared_at=_iso(opened_at + timedelta(minutes=5)),
                reviewed_at=None if case_id == conflict_case_id else _iso(
                    opened_at + timedelta(minutes=10)
                ),
                reviewed_by=None if case_id == conflict_case_id else 1,
                review_notes=None if case_id == conflict_case_id else
                "Synthetic conflict record retained for audit.",
            ))
            flagged_for_conflict[case_id] = conflict_reviewer_id

        evidence_ids: list[int] = []
        pre_decision_evidence = []
        for sequence in (1, 2):
            evidence_id = len(tables["evidence_items"]) + 1
            evidence_ids.append(evidence_id)
            evidence_time = opened_at + timedelta(minutes=30 * sequence)
            evidence_type = (
                "SIMILARITY_REPORT" if sequence == 1 else "EXPLANATION"
            )
            evidence = _new_row(
                "evidence_items",
                id=evidence_id,
                evidence_code=f"EVD-{case_id:06d}-{sequence:03d}",
                case_id=case_id,
                evidence_type=evidence_type,
                title=(
                    "Synthetic similarity report" if sequence == 1
                    else "Synthetic learner explanation"
                ),
                description=(
                    "Synthetic reference only; not a real learner record."
                ),
                source_reference=(
                    f"synthetic://cases/{case_id:06d}/evidence/{sequence:03d}"
                ),
                sha256_hash=hashlib.sha256(
                    f"{seed}:evidence:{case_id}:{sequence}".encode("utf-8")
                ).hexdigest(),
                mime_type="application/json",
                file_size_bytes=128 + sequence,
                collected_at=_iso(evidence_time),
                added_at=_iso(evidence_time),
                added_by=case_reviewer_id,
            )
            tables["evidence_items"].append(evidence)
            pre_decision_evidence.append(evidence)
        evidence_ids_by_case[case_id] = evidence_ids

        submission_truth = truth_by_submission[submission_id]
        truth_label = submission_truth["truth_label"]
        score = score_by_submission[submission_id]
        expected_decision = submission_truth["expected_decision"]
        if case_id == auto_guilt_case_id:
            outcome = "BREACH_ESTABLISHED"
            rationale = (
                "INJECTED ANOMALY: the similarity flag was treated as conclusive "
                "proof of guilt, without independent evidence evaluation."
            )
        elif (
            truth_label == "LEGITIMATE_OVERLAP"
            and case_id % 3 == 0
        ):
            outcome = "BREACH_ESTABLISHED"
            rationale = (
                "Synthetic reviewer error: legitimate quotation or template "
                "overlap was not adequately considered."
            )
        elif truth_label == "LEGITIMATE_OVERLAP":
            outcome = "NO_BREACH"
            rationale = (
                "Human review found the observed overlap attributable to "
                "synthetic legitimate quotation or shared template material."
            )
        elif score >= 60:
            outcome = "BREACH_ESTABLISHED"
            rationale = (
                "Human review considered the synthetic source matches and "
                "learner explanation before recording this outcome."
            )
        elif case_id % 5 == 0:
            outcome = "NO_BREACH"
            rationale = "Human review did not find sufficient evidence of a breach."
        else:
            outcome = "INSUFFICIENT_EVIDENCE"
            rationale = "The synthetic evidence is insufficient to establish a breach."

        decision_id = case_id
        decision_code = f"DEC-2026-{decision_id:06d}"
        decision = _new_row(
            "case_decisions",
            id=decision_id,
            decision_code=decision_code,
            case_id=case_id,
            reviewer_id=case_reviewer_id,
            outcome=outcome,
            rationale=rationale,
            decided_at=_iso(decision_at),
        )
        tables["case_decisions"].append(decision)
        decision_by_case[case_id] = decision
        submission_truth["actual_decision"] = outcome
        submission_truth["expected_decision"] = expected_decision

        for evidence in pre_decision_evidence:
            tables["decision_evidence"].append(_new_row(
                "decision_evidence",
                id=len(tables["decision_evidence"]) + 1,
                decision_id=decision_id,
                evidence_id=evidence["id"],
                evidence_code_snapshot=evidence["evidence_code"],
                evidence_title_snapshot=evidence["title"],
                evidence_type_snapshot=evidence["evidence_type"],
            ))

        if case_id == late_evidence_case_id:
            late_id = len(tables["evidence_items"]) + 1
            evidence_ids.append(late_id)
            late_at = decision_at + timedelta(minutes=30)
            tables["evidence_items"].append(_new_row(
                "evidence_items",
                id=late_id,
                evidence_code=f"EVD-{case_id:06d}-003",
                case_id=case_id,
                evidence_type="OTHER",
                title="Synthetic evidence added after decision",
                description=(
                    "INJECTED ANOMALY: evidence added after decision without "
                    "a corresponding case event."
                ),
                source_reference=f"synthetic://cases/{case_id:06d}/evidence/003",
                sha256_hash=hashlib.sha256(
                    f"{seed}:evidence:{case_id}:3".encode("utf-8")
                ).hexdigest(),
                mime_type="application/json",
                file_size_bytes=131,
                collected_at=_iso(late_at),
                added_at=_iso(late_at),
                added_by=case_reviewer_id,
            ))
            evidence_ids_by_case[case_id] = evidence_ids

        event_rows = [
            ("CASE_OPENED", "Case opened from a similarity flag.", None, "SYSTEM", opened_at),
            (
                "REVIEWER_ASSIGNED",
                f"Reviewer {case_reviewer_id} assigned to the case.",
                case_reviewer_id,
                "REVIEWER",
                assigned_at,
            ),
            (
                "STATUS_CHANGED",
                "Status changed from ASSIGNED to UNDER_REVIEW.",
                case_reviewer_id,
                "REVIEWER",
                opened_at + timedelta(minutes=20),
            ),
        ]
        if case_id == auto_guilt_case_id:
            event_rows.append((
                "FLAG_AUTOMATICALLY_TREATED_AS_GUILT",
                "INJECTED ANOMALY: a flag was treated as a finding of guilt.",
                case_reviewer_id,
                "REVIEWER",
                opened_at + timedelta(minutes=25),
            ))
        for evidence in pre_decision_evidence:
            event_rows.append((
                "EVIDENCE_ADDED",
                f"Evidence {evidence['evidence_code']} added before the decision.",
                case_reviewer_id,
                "REVIEWER",
                datetime.fromisoformat(evidence["added_at"]),
            ))
        event_rows.extend([
            (
                "STATUS_CHANGED",
                "Status changed from UNDER_REVIEW to DECISION_PENDING.",
                case_reviewer_id,
                "REVIEWER",
                decision_at - timedelta(minutes=10),
            ),
            (
                "DECISION_RECORDED",
                f"Decision {decision_code} recorded: {outcome}.",
                case_reviewer_id,
                "REVIEWER",
                decision_at,
            ),
            (
                "STATUS_CHANGED",
                "Status changed from DECISION_PENDING to CLOSED.",
                case_reviewer_id,
                "REVIEWER",
                closed_at,
            ),
        ])
        for event_type, description, actor_id, actor_role, event_at in sorted(
            event_rows, key=lambda event: event[4]
        ):
            tables["case_events"].append(_new_row(
                "case_events",
                id=len(tables["case_events"]) + 1,
                case_id=case_id,
                event_type=event_type,
                description=description,
                actor_id=actor_id,
                actor_role=actor_role,
                created_at=_iso(event_at),
            ))

    success_case_ids = [
        case_id
        for case_id, decision in decision_by_case.items()
        if (
            case_id != auto_guilt_case_id
            and case_id != appeal_without_reviewer_case_id
            and truth_by_submission[case_submission_ids[case_id - 1]]["truth_label"]
            == "LEGITIMATE_OVERLAP"
            and decision["outcome"] == "BREACH_ESTABLISHED"
        )
    ]
    for case_id in case_id_by_submission.values():
        if (
            case_id != auto_guilt_case_id
            and case_id != appeal_without_reviewer_case_id
            and truth_by_submission[case_submission_ids[case_id - 1]]["truth_label"]
            == "LEGITIMATE_OVERLAP"
            and decision_by_case[case_id]["outcome"] == "NO_BREACH"
            and case_id % 3 == 0
        ):
            decision_by_case[case_id]["outcome"] = "BREACH_ESTABLISHED"
            decision_by_case[case_id]["rationale"] = (
                "Synthetic reviewer error: legitimate overlap was overlooked."
            )
            success_case_ids.append(case_id)
            tables["case_decisions"][case_id - 1]["outcome"] = "BREACH_ESTABLISHED"
            tables["case_decisions"][case_id - 1]["rationale"] = (
                "Synthetic reviewer error: legitimate overlap was overlooked."
            )
            truth_by_submission[case_submission_ids[case_id - 1]][
                "actual_decision"
            ] = "BREACH_ESTABLISHED"

    appeal_total = min(cases_count, max(4, cases_count // 5))
    anomaly_appeal_case = appeal_without_reviewer_case_id
    eligible_case_ids = [
        case_id for case_id in range(1, cases_count + 1)
        if case_id not in {auto_guilt_case_id, anomaly_appeal_case}
    ]
    success_case_ids = sorted(set(success_case_ids))
    selected_appeal_cases = success_case_ids[: max(0, appeal_total - 1)]
    remaining = [
        case_id for case_id in eligible_case_ids
        if case_id not in selected_appeal_cases
    ]
    rng.shuffle(remaining)
    selected_appeal_cases.extend(
        remaining[: max(0, appeal_total - 1 - len(selected_appeal_cases))]
    )
    selected_appeal_cases.append(anomaly_appeal_case)
    selected_appeal_cases = sorted(set(selected_appeal_cases))

    appeal_id_by_case: dict[int, int] = {}
    for case_id in selected_appeal_cases:
        appeal_id = len(tables["appeals"]) + 1
        appeal_id_by_case[case_id] = appeal_id
        submission_id = case_submission_ids[case_id - 1]
        decision = decision_by_case[case_id]
        case_opened = case_time_by_id[case_id]
        submitted_at = datetime.fromisoformat(decision["decided_at"]) + timedelta(days=2)
        truth_label = truth_by_submission[submission_id]["truth_label"]
        is_success = (
            truth_label == "LEGITIMATE_OVERLAP"
            and decision["outcome"] == "BREACH_ESTABLISHED"
            and case_id != auto_guilt_case_id
            and case_id != anomaly_appeal_case
        )
        anomalous = case_id == anomaly_appeal_case

        if anomalous:
            status = "DECIDED"
            outcome = "OVERTURNED"
            rationale = (
                "INJECTED ANOMALY: appeal marked decided without an independent reviewer."
            )
            assigned_reviewer_id = None
            assigned_at = None
            resolved_at = submitted_at + timedelta(days=5)
        else:
            appeal_position = appeal_id
            if is_success or appeal_position % 4 not in {0, 1, 2}:
                status = "DECIDED"
            elif appeal_position % 4 == 0:
                status = "SUBMITTED"
            elif appeal_position % 4 == 1:
                status = "UNDER_REVIEW"
            else:
                status = "WITHDRAWN"

            if is_success:
                outcome = "OVERTURNED"
            elif decision["outcome"] == "INSUFFICIENT_EVIDENCE":
                outcome = "REMANDED"
            else:
                outcome = "UPHELD"

            if status == "DECIDED":
                rationale = (
                    "Independent review considered the original evidence, "
                    "appeal grounds, and applicable synthetic policy."
                )
                assigned_reviewer_id = next(
                    reviewer_id
                    for reviewer_id in active_reviewer_ids
                    if reviewer_id != decision["reviewer_id"]
                    and reviewer_id != reviewer_by_case[case_id]
                    and flagged_for_conflict.get(case_id) != reviewer_id
                )
                assigned_at = submitted_at + timedelta(hours=2)
                resolved_at = assigned_at + timedelta(days=3)
            elif status == "UNDER_REVIEW":
                rationale = None
                assigned_reviewer_id = next(
                    reviewer_id
                    for reviewer_id in active_reviewer_ids
                    if reviewer_id != decision["reviewer_id"]
                    and reviewer_id != reviewer_by_case[case_id]
                    and flagged_for_conflict.get(case_id) != reviewer_id
                )
                assigned_at = submitted_at + timedelta(hours=2)
                resolved_at = None
                outcome = None
            elif status == "WITHDRAWN":
                rationale = None
                assigned_reviewer_id = None
                assigned_at = None
                resolved_at = submitted_at + timedelta(days=1)
                outcome = None
            else:
                rationale = None
                assigned_reviewer_id = None
                assigned_at = None
                resolved_at = None
                outcome = None

        appeal_row = _new_row(
            "appeals",
            id=appeal_id,
            appeal_code=f"APL-{case_id:06d}-01",
            decision_id=decision["id"],
            learner_id=tables["cases"][case_id - 1]["learner_id"],
            assigned_reviewer_id=assigned_reviewer_id,
            grounds=(
                "The original review may not have accounted for all "
                "synthetic contextual evidence."
            ),
            status=status,
            outcome=outcome,
            outcome_rationale=rationale,
            submitted_at=_iso(submitted_at),
            assigned_at=_iso(assigned_at),
            resolved_at=_iso(resolved_at),
        )
        tables["appeals"].append(appeal_row)

        tables["appeal_events"].append(_new_row(
            "appeal_events",
            id=len(tables["appeal_events"]) + 1,
            appeal_id=appeal_id,
            event_type="APPEAL_SUBMITTED",
            description="Learner submitted a synthetic appeal.",
            actor_id=appeal_row["learner_id"],
            actor_role="LEARNER",
            created_at=_iso(submitted_at),
        ))
        if assigned_reviewer_id is not None:
            tables["appeal_events"].append(_new_row(
                "appeal_events",
                id=len(tables["appeal_events"]) + 1,
                appeal_id=appeal_id,
                event_type="REVIEWER_ASSIGNED",
                description="Independent synthetic appeal reviewer assigned.",
                actor_id=assigned_reviewer_id,
                actor_role="ADMIN",
                created_at=appeal_row["assigned_at"],
            ))
        if status == "WITHDRAWN":
            tables["appeal_events"].append(_new_row(
                "appeal_events",
                id=len(tables["appeal_events"]) + 1,
                appeal_id=appeal_id,
                event_type="APPEAL_WITHDRAWN",
                description="Learner withdrew the synthetic appeal.",
                actor_id=appeal_row["learner_id"],
                actor_role="LEARNER",
                created_at=appeal_row["resolved_at"],
            ))
        if status == "DECIDED" and not anomalous:
            tables["appeal_events"].append(_new_row(
                "appeal_events",
                id=len(tables["appeal_events"]) + 1,
                appeal_id=appeal_id,
                event_type="APPEAL_DECIDED",
                description=f"Independent appeal outcome recorded: {outcome}.",
                actor_id=assigned_reviewer_id,
                actor_role="INDEPENDENT_REVIEWER",
                created_at=appeal_row["resolved_at"],
            ))

        for evidence_id in evidence_ids_by_case[case_id][:2]:
            evidence = tables["evidence_items"][evidence_id - 1]
            tables["appeal_evidence"].append(_new_row(
                "appeal_evidence",
                id=len(tables["appeal_evidence"]) + 1,
                appeal_id=appeal_id,
                evidence_id=evidence_id,
                evidence_code_snapshot=evidence["evidence_code"],
                evidence_title_snapshot=evidence["title"],
                evidence_type_snapshot=evidence["evidence_type"],
                added_by=appeal_row["learner_id"],
                added_at=_iso(submitted_at + timedelta(minutes=10)),
            ))

        truth_by_submission[submission_id]["actual_decision"] = decision["outcome"]

    if cases_count >= 4:
        anomaly_assign_id = conflict_case_id
        anomaly_evidence_id = tables["evidence_items"][
            evidence_ids_by_case[late_evidence_case_id][-1] - 1
        ]["id"]
        anomaly_appeal_id = appeal_id_by_case.get(anomaly_appeal_case)
        anomaly_specs = [
            (
                "FLAG_TREATED_AS_GUILT",
                "CASE",
                auto_guilt_case_id,
                case_submission_ids[auto_guilt_case_id - 1],
                auto_guilt_case_id,
                "A flag must request human review and cannot be treated as guilt.",
                "A decision rationale explicitly treats a flag as conclusive guilt.",
            ),
            (
                "REVIEWER_CONFLICT",
                "CASE_ASSIGNMENT",
                anomaly_assign_id,
                case_submission_ids[conflict_case_id - 1],
                conflict_case_id,
                "A reviewer with a pending conflict must not be assigned.",
                "The injected assignment has CONFLICT_DETECTED and a pending conflict record.",
            ),
            (
                "EVIDENCE_AFTER_DECISION_WITHOUT_HISTORY",
                "EVIDENCE_ITEM",
                anomaly_evidence_id,
                case_submission_ids[late_evidence_case_id - 1],
                late_evidence_case_id,
                "Evidence added after decision must be recorded in case history.",
                "Evidence timestamp is later than the decision and no matching event exists.",
            ),
            (
                "APPEAL_CLOSED_WITHOUT_INDEPENDENT_REVIEW",
                "APPEAL",
                anomaly_appeal_id,
                case_submission_ids[anomaly_appeal_case - 1],
                anomaly_appeal_case,
                "A decided appeal requires an independent assigned reviewer and audit event.",
                "The injected appeal is DECIDED without assigned_reviewer_id or APPEAL_DECIDED event.",
            ),
        ]
        for issue_type, record_type, record_id, submission_id, case_id, expected, actual in anomaly_specs:
            truth.append({
                "record_type": record_type,
                "record_id": record_id,
                "submission_id": submission_id,
                "case_id": case_id,
                "truth_label": "INJECTED_ANOMALY",
                "expected_review_action": None,
                "expected_decision": None,
                "actual_decision": decision_by_case.get(case_id, {}).get("outcome"),
                "issue_type": issue_type,
                "expected_behavior": expected,
                "actual_behavior": actual,
            })

    return tables, truth


def _validate_unique(rows: list[dict[str, Any]], field: str, table: str) -> list[str]:
    values = [row[field] for row in rows]
    if len(values) != len(set(values)):
        return [f"{table}.{field} contains duplicate values."]
    return []


def validate_dataset(
    tables: dict[str, list[dict[str, Any]]],
    truth: list[dict[str, Any]],
    submissions_count: int,
    flags_count: int,
    cases_count: int,
) -> dict[str, Any]:
    errors: list[str] = []
    for table, columns in TABLE_COLUMNS.items():
        rows = tables.get(table)
        if rows is None:
            errors.append(f"Missing table data: {table}")
            continue
        if any(set(row) != set(columns) for row in rows):
            errors.append(f"{table} has a row with an unexpected column set.")
        errors.extend(_validate_unique(rows, "id", table))

    expected_counts = {
        "submissions": submissions_count,
        "similarity_reports": submissions_count,
        "flags": flags_count,
        "cases": cases_count,
        "case_decisions": cases_count,
    }
    for table, expected in expected_counts.items():
        if len(tables.get(table, [])) != expected:
            errors.append(
                f"{table} count is {len(tables.get(table, []))}; expected {expected}."
            )

    unique_codes = {
        "learners": "learner_code",
        "assessments": "assessment_code",
        "reviewers": "reviewer_code",
        "integrity_rules": "rule_code",
        "submissions": "submission_code",
        "similarity_reports": "report_code",
        "flags": "flag_code",
        "cases": "case_code",
        "evidence_items": "evidence_code",
        "case_decisions": "decision_code",
        "appeals": "appeal_code",
    }
    for table, field in unique_codes.items():
        errors.extend(_validate_unique(tables[table], field, table))

    allowed_values = {
        "learners": {"status": {"ACTIVE"}},
        "assessments": {
            "assessment_type": {"ASSIGNMENT", "PROJECT", "EXAM"},
            "status": {"PUBLISHED"},
        },
        "reviewers": {"status": {"ACTIVE", "ON_LEAVE", "INACTIVE"}},
        "integrity_rules": {
            "action": {"INFORMATION", "REVIEW", "PRIORITY_REVIEW"},
        },
        "submissions": {"status": {"SUBMITTED"}},
        "similarity_reports": {"status": {"COMPLETED"}},
        "similarity_matches": {
            "source_type": set(SOURCES),
        },
        "flags": {
            "flag_type": {"REVIEW", "PRIORITY_REVIEW"},
            "status": {"OPEN"},
        },
        "cases": {
            "status": {"OPEN", "ASSIGNED", "UNDER_REVIEW", "DECISION_PENDING", "CLOSED"},
            "priority": {"LOW", "NORMAL", "HIGH", "URGENT"},
        },
        "case_assignments": {
            "conflict_status": {"CLEARED", "CONFLICT_DETECTED"},
            "status": {"COMPLETED"},
        },
        "reviewer_conflicts": {
            "conflict_type": {"ACADEMIC", "PROFESSIONAL"},
            "status": {"PENDING", "CONFIRMED"},
        },
        "case_decisions": {
            "outcome": {
                "BREACH_ESTABLISHED", "NO_BREACH",
                "INSUFFICIENT_EVIDENCE", "REFERRED_FOR_FURTHER_REVIEW",
            },
        },
        "appeals": {
            "status": {"SUBMITTED", "UNDER_REVIEW", "DECIDED", "WITHDRAWN"},
            "outcome": {"UPHELD", "OVERTURNED", "REMANDED", None},
        },
    }
    for table, fields in allowed_values.items():
        for field, values in fields.items():
            if any(row[field] not in values for row in tables[table]):
                errors.append(f"{table}.{field} contains a disallowed value.")

    ids_by_table = {
        table: {row["id"] for row in rows}
        for table, rows in tables.items()
    }

    assessments_by_id = {row["id"]: row for row in tables["assessments"]}
    for submission in tables["submissions"]:
        assessment = assessments_by_id[submission["assessment_id"]]
        submitted_at = datetime.fromisoformat(submission["submitted_at"])
        if not (
            datetime.fromisoformat(assessment["created_at"])
            <= submitted_at
            <= datetime.fromisoformat(assessment["due_date"])
        ):
            errors.append(
                f"Submission {submission['id']} falls outside its assessment dates."
            )

    report_by_id = {row["id"]: row for row in tables["similarity_reports"]}
    submission_by_id = {row["id"]: row for row in tables["submissions"]}
    for report in tables["similarity_reports"]:
        submission = submission_by_id[report["submission_id"]]
        if datetime.fromisoformat(submission["submitted_at"]) > datetime.fromisoformat(
            report["analyzed_at"]
        ):
            errors.append(f"Report {report['id']} predates its submission.")

    decision_by_id = {row["id"]: row for row in tables["case_decisions"]}
    for appeal in tables["appeals"]:
        decision = decision_by_id[appeal["decision_id"]]
        if datetime.fromisoformat(appeal["submitted_at"]) < datetime.fromisoformat(
            decision["decided_at"]
        ):
            errors.append(f"Appeal {appeal['id']} predates its original decision.")
        if appeal["assigned_at"] is not None and datetime.fromisoformat(
            appeal["assigned_at"]
        ) < datetime.fromisoformat(appeal["submitted_at"]):
            errors.append(f"Appeal {appeal['id']} was assigned before submission.")
        if appeal["resolved_at"] is not None and datetime.fromisoformat(
            appeal["resolved_at"]
        ) < datetime.fromisoformat(appeal["submitted_at"]):
            errors.append(f"Appeal {appeal['id']} was resolved before submission.")

    def check_fk(table: str, field: str, target: str, optional: bool = False) -> None:
        for row in tables[table]:
            value = row[field]
            if optional and value is None:
                continue
            if value not in ids_by_table[target]:
                errors.append(f"{table}.{field} references missing {target} ID {value}.")
                return

    foreign_keys = [
        ("submissions", "learner_id", "learners", False),
        ("submissions", "assessment_id", "assessments", False),
        ("similarity_reports", "submission_id", "submissions", False),
        ("similarity_matches", "report_id", "similarity_reports", False),
        ("flags", "submission_id", "submissions", False),
        ("flags", "report_id", "similarity_reports", False),
        ("flags", "integrity_rule_id", "integrity_rules", False),
        ("cases", "learner_id", "learners", False),
        ("case_flags", "case_id", "cases", False),
        ("case_flags", "flag_id", "flags", False),
        ("case_assignments", "case_id", "cases", False),
        ("case_assignments", "reviewer_id", "reviewers", False),
        ("reviewer_conflicts", "case_id", "cases", False),
        ("reviewer_conflicts", "reviewer_id", "reviewers", False),
        ("case_events", "case_id", "cases", False),
        ("evidence_items", "case_id", "cases", False),
        ("case_decisions", "case_id", "cases", False),
        ("case_decisions", "reviewer_id", "reviewers", False),
        ("decision_evidence", "decision_id", "case_decisions", False),
        ("decision_evidence", "evidence_id", "evidence_items", False),
        ("appeals", "decision_id", "case_decisions", False),
        ("appeals", "learner_id", "learners", False),
        ("appeals", "assigned_reviewer_id", "reviewers", True),
        ("appeal_evidence", "appeal_id", "appeals", False),
        ("appeal_evidence", "evidence_id", "evidence_items", False),
        ("appeal_events", "appeal_id", "appeals", False),
    ]
    for table, field, target, optional in foreign_keys:
        check_fk(table, field, target, optional)

    case_flags = tables["case_flags"]
    errors.extend(_validate_unique(case_flags, "flag_id", "case_flags"))
    errors.extend(_validate_unique(tables["appeal_evidence"], "evidence_id", "appeal_evidence"))
    errors.extend(_validate_unique(tables["appeals"], "decision_id", "appeals"))

    report_by_submission = {
        row["submission_id"]: row for row in tables["similarity_reports"]
    }
    rule_by_id = {row["id"]: row for row in tables["integrity_rules"]}
    flags_by_submission = {
        row["submission_id"]: row for row in tables["flags"]
    }
    matches_by_report: dict[int, list[dict[str, Any]]] = {}
    for match in tables["similarity_matches"]:
        matches_by_report.setdefault(match["report_id"], []).append(match)
    for submission in tables["submissions"]:
        submission_id = submission["id"]
        report = report_by_submission.get(submission_id)
        if not report:
            errors.append(f"Submission {submission_id} has no similarity report.")
            continue
        score = report["overall_score"]
        report_parts = (
            report["quotation_percentage"]
            + report["template_percentage"]
            + report["internet_percentage"]
        )
        if not 0 <= score <= 100 or round(report_parts, 2) != score:
            errors.append(f"Report fields do not reconcile for report {report['id']}.")
        parts = matches_by_report.get(report["id"], [])
        if round(sum(part["matched_percentage"] for part in parts), 2) != score:
            errors.append(f"Similarity components do not reconcile for report {report['id']}.")
        should_flag = score >= 40
        has_flag = submission_id in flags_by_submission
        if should_flag != has_flag:
            errors.append(f"Threshold/flag mismatch for submission {submission_id}.")
        if has_flag:
            flag = flags_by_submission[submission_id]
            rule = rule_by_id[flag["integrity_rule_id"]]
            if not rule["min_similarity"] <= score <= rule["max_similarity"]:
                errors.append(f"Flag {flag['id']} references a nonmatching rule.")
            if flag["flag_type"] != rule["action"]:
                errors.append(f"Flag {flag['id']} action differs from its rule.")

    cases_by_id = {row["id"]: row for row in tables["cases"]}
    flags_by_id = {row["id"]: row for row in tables["flags"]}
    submissions_by_id = {row["id"]: row for row in tables["submissions"]}
    decisions_by_case = {row["case_id"]: row for row in tables["case_decisions"]}
    assignments_by_case = {
        row["case_id"]: row for row in tables["case_assignments"]
    }
    for case_id, case in cases_by_id.items():
        assignment = assignments_by_case[case_id]
        decision = decisions_by_case[case_id]
        for earlier, later, description in (
            (case["opened_at"], assignment["assigned_at"], "assignment"),
            (assignment["assigned_at"], decision["decided_at"], "decision"),
            (decision["decided_at"], case["closed_at"], "closure"),
        ):
            if datetime.fromisoformat(earlier) > datetime.fromisoformat(later):
                errors.append(f"Case {case_id} has invalid {description} chronology.")
        event_times = [
            datetime.fromisoformat(event["created_at"])
            for event in tables["case_events"]
            if event["case_id"] == case_id
        ]
        if event_times != sorted(event_times):
            errors.append(f"Case {case_id} events are not chronological.")

    for link in case_flags:
        case = cases_by_id[link["case_id"]]
        flag = flags_by_id[link["flag_id"]]
        if case["learner_id"] != submissions_by_id[flag["submission_id"]]["learner_id"]:
            errors.append(f"CaseFlag {link['id']} joins records for different learners.")

    assigned_reviewer_by_case = {
        row["case_id"]: row["reviewer_id"]
        for row in tables["case_assignments"]
    }
    evidence_by_id = {row["id"]: row for row in tables["evidence_items"]}
    for snapshot in tables["decision_evidence"]:
        evidence = evidence_by_id[snapshot["evidence_id"]]
        decision = next(
            row for row in tables["case_decisions"]
            if row["id"] == snapshot["decision_id"]
        )
        if evidence["case_id"] != decision["case_id"]:
            errors.append(f"DecisionEvidence {snapshot['id']} crosses case boundaries.")
        if datetime.fromisoformat(evidence["added_at"]) > datetime.fromisoformat(
            decision["decided_at"]
        ):
            errors.append(f"DecisionEvidence {snapshot['id']} postdates the decision.")

    events_by_case: dict[int, list[dict[str, Any]]] = {}
    for event in tables["case_events"]:
        events_by_case.setdefault(event["case_id"], []).append(event)
    expected_issue_types = {
        "FLAG_TREATED_AS_GUILT",
        "REVIEWER_CONFLICT",
        "EVIDENCE_AFTER_DECISION_WITHOUT_HISTORY",
        "APPEAL_CLOSED_WITHOUT_INDEPENDENT_REVIEW",
    }
    anomalies = [row for row in truth if row["record_type"] != "SUBMISSION"]
    actual_issue_types = {row["issue_type"] for row in anomalies}
    if actual_issue_types != expected_issue_types:
        errors.append(
            "Ground truth anomaly labels do not match the injected edge-case set."
        )

    anomaly_by_type = {row["issue_type"]: row for row in anomalies}
    anomalous_appeal_ids = {
        row["record_id"]
        for row in anomalies
        if row["issue_type"] == "APPEAL_CLOSED_WITHOUT_INDEPENDENT_REVIEW"
    }
    guilt = anomaly_by_type.get("FLAG_TREATED_AS_GUILT")
    if guilt:
        decision = decisions_by_case[guilt["case_id"]]
        if (
            "INJECTED ANOMALY" not in decision["rationale"]
            or not any(
                event["event_type"] == "FLAG_AUTOMATICALLY_TREATED_AS_GUILT"
                for event in events_by_case[guilt["case_id"]]
            )
        ):
            errors.append("The labelled flag-as-guilt scenario was not materialized.")

    conflict = anomaly_by_type.get("REVIEWER_CONFLICT")
    if conflict:
        assignment = next(
            row for row in tables["case_assignments"]
            if row["id"] == conflict["record_id"]
        )
        if (
            assignment["conflict_status"] != "CONFLICT_DETECTED"
            or not any(
                row["case_id"] == conflict["case_id"]
                and row["reviewer_id"] == assignment["reviewer_id"]
                and row["status"] in {"PENDING", "CONFIRMED"}
                for row in tables["reviewer_conflicts"]
            )
        ):
            errors.append("The labelled reviewer-conflict scenario was not materialized.")

    late = anomaly_by_type.get("EVIDENCE_AFTER_DECISION_WITHOUT_HISTORY")
    if late:
        item = evidence_by_id[late["record_id"]]
        decision = decisions_by_case[late["case_id"]]
        if (
            datetime.fromisoformat(item["added_at"])
            <= datetime.fromisoformat(decision["decided_at"])
            or any(
                event["event_type"] == "EVIDENCE_ADDED"
                and item["evidence_code"] in event["description"]
                for event in events_by_case[late["case_id"]]
            )
        ):
            errors.append("The labelled late-evidence anomaly was not materialized.")

    anomalous_appeal = anomaly_by_type.get(
        "APPEAL_CLOSED_WITHOUT_INDEPENDENT_REVIEW"
    )
    if anomalous_appeal:
        appeal = next(
            row for row in tables["appeals"]
            if row["id"] == anomalous_appeal["record_id"]
        )
        if (
            appeal["status"] != "DECIDED"
            or appeal["assigned_reviewer_id"] is not None
            or any(
                event["appeal_id"] == appeal["id"]
                and event["event_type"] == "APPEAL_DECIDED"
                for event in tables["appeal_events"]
            )
        ):
            errors.append("The labelled appeal-without-independent-review anomaly is absent.")

    appeal_by_decision = {
        row["decision_id"]: row for row in tables["appeals"]
    }
    active_conflicts = {
        (row["case_id"], row["reviewer_id"])
        for row in tables["reviewer_conflicts"]
        if row["status"] in {"PENDING", "CONFIRMED"}
    }
    appeal_events_by_id: dict[int, list[dict[str, Any]]] = {}
    for event in tables["appeal_events"]:
        appeal_events_by_id.setdefault(event["appeal_id"], []).append(event)
    for appeal in tables["appeals"]:
        decision = decision_by_id[appeal["decision_id"]]
        events = appeal_events_by_id.get(appeal["id"], [])
        event_times = [
            datetime.fromisoformat(event["created_at"]) for event in events
        ]
        if event_times != sorted(event_times):
            errors.append(f"Appeal {appeal['id']} events are not chronological.")
        if appeal["id"] in anomalous_appeal_ids:
            continue
        if appeal["status"] == "DECIDED" and (
            appeal["outcome"] is None or appeal["outcome_rationale"] is None
        ):
            errors.append(f"Decided appeal {appeal['id']} lacks an outcome or rationale.")
        if appeal["status"] == "UNDER_REVIEW" and (
            appeal["assigned_reviewer_id"] is None or appeal["assigned_at"] is None
        ):
            errors.append(f"Appeal {appeal['id']} is under review without an assignment.")
        if appeal["status"] in {"SUBMITTED", "WITHDRAWN"} and (
            appeal["outcome"] is not None
        ):
            errors.append(f"Unresolved appeal {appeal['id']} has a final outcome.")
        if appeal["assigned_reviewer_id"] is not None:
            if appeal["assigned_reviewer_id"] == decision["reviewer_id"]:
                errors.append(f"Appeal {appeal['id']} reuses the original reviewer.")
            if appeal["assigned_reviewer_id"] == assigned_reviewer_by_case.get(
                decision["case_id"]
            ):
                errors.append(f"Appeal {appeal['id']} reuses the case reviewer.")
            if (
                decision["case_id"], appeal["assigned_reviewer_id"]
            ) in active_conflicts:
                errors.append(f"Appeal {appeal['id']} reviewer has an active conflict.")
        if appeal["status"] == "DECIDED" and (
            appeal["assigned_reviewer_id"] is None
            or not any(event["event_type"] == "APPEAL_DECIDED" for event in events)
        ):
            errors.append(f"Decided appeal {appeal['id']} lacks independent review history.")
    submission_by_flag = {
        row["id"]: row["submission_id"] for row in tables["flags"]
    }
    submission_by_case = {
        link["case_id"]: submission_by_flag[link["flag_id"]]
        for link in tables["case_flags"]
    }
    truth_by_submission = {
        row["submission_id"]: row
        for row in truth
        if row["record_type"] == "SUBMISSION"
    }
    success_count = sum(
        1
        for case_id, decision in decisions_by_case.items()
        if (
            decision["outcome"] == "BREACH_ESTABLISHED"
            and truth_by_submission[submission_by_case[case_id]][
                "truth_label"
            ] == "LEGITIMATE_OVERLAP"
            and decision["id"] in appeal_by_decision
            and appeal_by_decision[decision["id"]]["status"] == "DECIDED"
            and appeal_by_decision[decision["id"]]["outcome"] == "OVERTURNED"
        )
    )
    if cases_count >= 30 and success_count == 0:
        errors.append("No successful appeal was generated for a known false positive.")

    expected_counts_actual = {
        table: len(rows) for table, rows in tables.items()
    }
    score_distribution = Counter(
        "INFORMATION" if row["overall_score"] < 40
        else "REVIEW" if row["overall_score"] < 70
        else "PRIORITY_REVIEW"
        for row in tables["similarity_reports"]
    )
    false_positive_flags = sum(
        1
        for submission_id in flags_by_submission
        if truth_by_submission[submission_id]["truth_label"] == "LEGITIMATE_OVERLAP"
    )
    return {
        "status": "FAILED" if errors else "PASS_WITH_EXPECTED_ANOMALIES",
        "errors": errors,
        "row_counts": expected_counts_actual,
        "metrics": {
            "review_action_distribution": dict(sorted(score_distribution.items())),
            "flagged_legitimate_overlap_count": false_positive_flags,
            "successful_appeal_count": success_count,
            "expected_anomaly_count": len(anomalies),
            "expected_anomaly_types": sorted(actual_issue_types),
        },
        "validation_checks": [
            "row counts, primary-key uniqueness, and business-code uniqueness",
            "foreign-key and bridge-table integrity",
            "allowed enum values",
            "assessment, submission, review, decision, and appeal date ordering",
            "threshold-to-flag reconciliation and rule actions",
            "similarity report and source component arithmetic",
            "case-to-submission learner joins",
            "decision evidence ownership and chronology",
            "case and appeal event chronology and lifecycle consistency",
            "independent appeal reviewer assignment",
            "ground-truth-labelled anomaly materialization",
            "successful appeal for a labelled legitimate-overlap false positive",
        ],
    }


DATA_DICTIONARY: dict[str, dict[str, Any]] = {
    "Learner": {
        "table": "learners",
        "cardinality": "One learner has many submissions, cases, and appeals.",
        "fields": {
            "id": ("integer", True, "positive, unique primary key", None, True),
            "learner_code": ("string", True, "LRN-2026-NNNNNN", None, True),
            "name": ("string", True, "synthetic display name", None, False),
            "email": ("string", True, "example.invalid domain", None, True),
            "department": ("string", True, "Computer Science|Mathematics|Engineering", None, False),
            "status": ("string", True, "ACTIVE", None, False),
        },
    },
    "Assessment": {
        "table": "assessments",
        "cardinality": "One assessment has many submissions.",
        "fields": {
            "id": ("integer", True, "positive, unique primary key", None, True),
            "assessment_code": ("string", True, "ASM-2026-NNNNNN", None, True),
            "title": ("string", True, "non-empty synthetic title", None, False),
            "description": ("string|null", False, "synthetic provenance statement", None, False),
            "assessment_type": ("string", True, "ASSIGNMENT|PROJECT|EXAM", None, False),
            "max_marks": ("integer", True, "positive", "marks", False),
            "due_date": ("datetime|null", False, "after created_at", "UTC-naive ISO datetime", False),
            "status": ("string", True, "PUBLISHED", None, False),
            "created_at": ("datetime", True, "2025-12-02 onward", "UTC-naive ISO datetime", False),
        },
    },
    "Submission": {
        "table": "submissions",
        "cardinality": "Each submission belongs to one learner and one assessment; one submission has one report in this dataset.",
        "fields": {
            "id": ("integer", True, "positive, unique primary key", None, True),
            "submission_code": ("string", True, "SUB-2026-NNNNNN", None, True),
            "learner_id": ("integer", True, "FK learners.id", None, False),
            "assessment_id": ("integer", True, "FK assessments.id", None, False),
            "submitted_at": ("datetime", True, "after assessment creation", "UTC-naive ISO datetime", False),
            "file_reference": ("string|null", False, "synthetic:// URI only", None, False),
            "content_hash": ("string|null", False, "SHA-256 hex of synthetic token", None, False),
            "version_number": ("integer", True, ">= 1", "version", False),
            "status": ("string", True, "SUBMITTED", None, False),
        },
    },
    "SimilarityReport": {
        "table": "similarity_reports",
        "cardinality": "Each report belongs to one submission; one report has many source-match rows.",
        "fields": {
            "id": ("integer", True, "positive primary key; matches submission ID in this synthetic dataset", None, True),
            "report_code": ("string", True, "SIM-<submission-id>-01", None, True),
            "submission_id": ("integer", True, "FK submissions.id", None, True),
            "overall_score": ("decimal", True, "0..100; sum of source components", "percentage points", False),
            "quotation_percentage": ("decimal", True, "0..overall_score", "percentage points", False),
            "template_percentage": ("decimal", True, "0..overall_score", "percentage points", False),
            "internet_percentage": ("decimal", True, "0..overall_score; quotation + template + internet reconciles to overall_score", "percentage points", False),
            "analyzed_at": ("datetime", True, "on or after submitted_at", "UTC-naive ISO datetime", False),
            "status": ("string", True, "COMPLETED", None, False),
        },
    },
    "IntegrityRule": {
        "table": "integrity_rules",
        "cardinality": "One rule applies to many flags; rule ranges do not overlap.",
        "fields": {
            "id": ("integer", True, "positive primary key", None, True),
            "rule_code": ("string", True, "INT-2026-NNNNNN", None, True),
            "rule_name": ("string", True, "non-empty", None, False),
            "min_similarity": ("integer", True, "0..100 inclusive; <= max_similarity", "percentage points", False),
            "max_similarity": ("integer", True, "0..100 inclusive; >= min_similarity", "percentage points", False),
            "action": ("string", True, "INFORMATION|REVIEW|PRIORITY_REVIEW", None, False),
            "description": ("string|null", False, "states review is not guilt", None, False),
            "created_at": ("datetime", True, "synthetic fixed date", "UTC-naive ISO datetime", False),
        },
    },
    "Case": {
        "table": "cases",
        "cardinality": "A case belongs to one learner; CaseFlag is a bridge from case to flags (one case to many flags, each flag at most one case); a case has many events, evidence items, assignments, and decisions.",
        "fields": {
            "id": ("integer", True, "positive primary key", None, True),
            "case_code": ("string", True, "CASE-2026-NNNNNN", None, True),
            "learner_id": ("integer", True, "FK learners.id", None, False),
            "title": ("string", True, "non-empty", None, False),
            "description": ("string|null", False, "states review is not a guilt finding", None, False),
            "status": ("string", True, "OPEN|ASSIGNED|UNDER_REVIEW|DECISION_PENDING|CLOSED; injected anomalies documented separately", None, False),
            "priority": ("string", True, "LOW|NORMAL|HIGH|URGENT", None, False),
            "opened_at": ("datetime", True, "after report analysis", "UTC-naive ISO datetime", False),
            "closed_at": ("datetime|null", False, "after decision time when CLOSED", "UTC-naive ISO datetime", False),
        },
    },
    "EvidenceItem": {
        "table": "evidence_items",
        "cardinality": "Each evidence item belongs to one case; DecisionEvidence and AppealEvidence are bridges with immutable metadata snapshots.",
        "fields": {
            "id": ("integer", True, "positive primary key", None, True),
            "evidence_code": ("string", True, "EVD-<case-id>-NNN", None, True),
            "case_id": ("integer", True, "FK cases.id", None, False),
            "evidence_type": ("string", True, "SIMILARITY_REPORT|EXPLANATION|OTHER", None, False),
            "title": ("string", True, "non-empty synthetic description", None, False),
            "description": ("string|null", False, "synthetic provenance; no personal data", None, False),
            "source_reference": ("string|null", False, "synthetic:// URI only", None, False),
            "sha256_hash": ("string|null", False, "64-character SHA-256 hex", None, False),
            "mime_type": ("string|null", False, "application/json", None, False),
            "file_size_bytes": ("integer|null", False, ">= 0", "bytes", False),
            "collected_at": ("datetime|null", False, "not after added_at", "UTC-naive ISO datetime", False),
            "added_at": ("datetime", True, "before decision except labelled anomaly", "UTC-naive ISO datetime", False),
            "added_by": ("integer|null", False, "reviewer ID or null", None, False),
        },
    },
    "Reviewer": {
        "table": "reviewers",
        "cardinality": "One reviewer may have many case assignments, decisions, conflicts, and assigned appeals.",
        "fields": {
            "id": ("integer", True, "positive primary key", None, True),
            "reviewer_code": ("string", True, "REV-2026-NNNNNN", None, True),
            "full_name": ("string", True, "synthetic display name", None, False),
            "email": ("string", True, "example.invalid domain", None, True),
            "department": ("string", True, "Computer Science|Mathematics|Engineering", None, False),
            "specialization": ("string|null", False, "synthetic review specialty", None, False),
            "max_active_cases": ("integer", True, "positive workload limit", "active cases plus appeals", False),
            "status": ("string", True, "ACTIVE|ON_LEAVE|INACTIVE", None, False),
            "created_at": ("datetime", True, "synthetic fixed date", "UTC-naive ISO datetime", False),
        },
    },
    "Decision": {
        "table": "case_decisions",
        "cardinality": "Each decision belongs to one case and one reviewer; DecisionEvidence links a decision to many evidence items with decision-time snapshots.",
        "fields": {
            "id": ("integer", True, "positive primary key", None, True),
            "decision_code": ("string", True, "DEC-2026-NNNNNN", None, True),
            "case_id": ("integer", True, "FK cases.id", None, False),
            "reviewer_id": ("integer", True, "FK reviewers.id", None, False),
            "outcome": ("string", True, "BREACH_ESTABLISHED|NO_BREACH|INSUFFICIENT_EVIDENCE|REFERRED_FOR_FURTHER_REVIEW", None, False),
            "rationale": ("string", True, "non-empty; anomaly rationale labelled", None, False),
            "decided_at": ("datetime", True, "after evidence reviewed and before case closure", "UTC-naive ISO datetime", False),
        },
    },
    "Appeal": {
        "table": "appeals",
        "cardinality": "One appeal per decision (unique FK); each appeal belongs to one learner, optionally has one assigned reviewer, and has many events/evidence snapshots.",
        "fields": {
            "id": ("integer", True, "positive primary key", None, True),
            "appeal_code": ("string", True, "APL-<case-id>-01", None, True),
            "decision_id": ("integer", True, "unique FK case_decisions.id", None, True),
            "learner_id": ("integer", True, "FK learners.id; must match case learner", None, False),
            "assigned_reviewer_id": ("integer|null", False, "FK reviewers.id; must differ from original decision-maker", None, False),
            "grounds": ("string", True, "10..10000 characters", None, False),
            "status": ("string", True, "SUBMITTED|UNDER_REVIEW|DECIDED|WITHDRAWN", None, False),
            "outcome": ("string|null", False, "UPHELD|OVERTURNED|REMANDED; set only when DECIDED", None, False),
            "outcome_rationale": ("string|null", False, "10..10000 characters when resolved", None, False),
            "submitted_at": ("datetime", True, "after original decision", "UTC-naive ISO datetime", False),
            "assigned_at": ("datetime|null", False, "on or after submitted_at", "UTC-naive ISO datetime", False),
            "resolved_at": ("datetime|null", False, "on or after submitted_at", "UTC-naive ISO datetime", False),
        },
    },
}


def _dictionary_payload() -> dict[str, Any]:
    result: dict[str, Any] = {}
    for entity, definition in DATA_DICTIONARY.items():
        fields = {}
        for name, (field_type, required, validation, units, unique) in definition["fields"].items():
            fields[name] = {
                "type": field_type,
                "required": required,
                "allowed_values_or_validation": validation,
                "units": units,
                "unique": unique,
            }
        result[entity] = {
            "table": definition["table"],
            "cardinality": definition["cardinality"],
            "lifecycle_states": _lifecycle_states(entity),
            "effective_date_notes": _effective_date_notes(entity),
            "fields": fields,
        }
    return result


def _lifecycle_states(entity: str) -> list[str]:
    states = {
        "Learner": ["ACTIVE"],
        "Assessment": ["DRAFT", "PUBLISHED", "ARCHIVED"],
        "Submission": ["SUBMITTED"],
        "SimilarityReport": ["COMPLETED"],
        "IntegrityRule": ["INFORMATION", "REVIEW", "PRIORITY_REVIEW"],
        "Case": ["OPEN", "ASSIGNED", "UNDER_REVIEW", "DECISION_PENDING", "CLOSED"],
        "EvidenceItem": ["APPENDED; metadata captured at added_at"],
        "Reviewer": ["ACTIVE", "ON_LEAVE", "INACTIVE"],
        "Decision": ["BREACH_ESTABLISHED", "NO_BREACH", "INSUFFICIENT_EVIDENCE", "REFERRED_FOR_FURTHER_REVIEW"],
        "Appeal": ["SUBMITTED", "UNDER_REVIEW", "DECIDED", "WITHDRAWN"],
    }
    return states[entity]


def _effective_date_notes(entity: str) -> str:
    if entity == "IntegrityRule":
        return (
            "The application model has created_at but no effective_from/effective_to. "
            "Synthetic rules are fixed for the dataset and do not claim historical validity."
        )
    if entity == "Appeal":
        return "submitted_at, assigned_at, and resolved_at record workflow timing."
    if entity == "Decision":
        return "decided_at is the decision effective timestamp."
    if entity in {"Case", "EvidenceItem", "Reviewer"}:
        return "Lifecycle timestamps are recorded where supported by the current model."
    return "No separate effective-date interval exists in the current model."


def _json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=True, sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")


def _sql_value(value: Any) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (int, float)):
        return str(value)
    return "'" + str(value).replace("\\", "\\\\").replace("'", "''") + "'"


def _write_sql(path: Path, tables: dict[str, list[dict[str, Any]]]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as output:
        output.write(
            "-- Synthetic seed data. Load only into a separately prepared database.\n"
            "-- Tables must already exist; do not run against production data.\n"
            "SET FOREIGN_KEY_CHECKS = 1;\n\n"
        )
        for table in SQL_TABLE_ORDER:
            rows = tables[table]
            if not rows:
                continue
            columns = TABLE_COLUMNS[table]
            column_sql = ", ".join(f"`{column}`" for column in columns)
            output.write(f"-- {table}: {len(rows)} rows\n")
            for start in range(0, len(rows), 250):
                chunk = rows[start:start + 250]
                values = ",\n".join(
                    "(" + ", ".join(_sql_value(row[column]) for column in columns) + ")"
                    for row in chunk
                )
                output.write(
                    f"INSERT INTO `{table}` ({column_sql}) VALUES\n{values};\n"
                )
            output.write("\n")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_exports(
    output_dir: Path,
    tables: dict[str, list[dict[str, Any]]],
    truth: list[dict[str, Any]],
    validation: dict[str, Any],
    seed: int,
    parameters: dict[str, int],
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    for table, rows in tables.items():
        path = output_dir / f"{table}.csv"
        with path.open("w", encoding="utf-8", newline="") as output:
            writer = csv.DictWriter(output, fieldnames=TABLE_COLUMNS[table])
            writer.writeheader()
            writer.writerows(rows)

    (output_dir / "data.json").write_bytes(_json_bytes({
        "generator_version": GENERATOR_VERSION,
        "seed": seed,
        "tables": tables,
    }))
    with (output_dir / "ground_truth.csv").open(
        "w", encoding="utf-8", newline=""
    ) as output:
        writer = csv.DictWriter(output, fieldnames=GROUND_TRUTH_COLUMNS)
        writer.writeheader()
        writer.writerows(truth)
    (output_dir / "ground_truth.json").write_bytes(_json_bytes(truth))
    (output_dir / "data_dictionary.json").write_bytes(
        _json_bytes(_dictionary_payload())
    )
    (output_dir / "validation_summary.json").write_bytes(_json_bytes(validation))
    _write_sql(output_dir / "seed.sql", tables)

    readme = f"""# Synthetic Academic Integrity Dataset

This dataset is generated locally by `scripts/generate_synthetic_data.py`.
Every name, email, content hash, match source, and evidence reference is
synthetic. Email addresses use the reserved `example.invalid` domain. No
external data or real learner work is used.

## Reproduce

From `backend`:

```powershell
python scripts\\generate_synthetic_data.py --seed {seed} --submissions {parameters['submissions']} --flags {parameters['flags']} --cases {parameters['cases']} --out generated_data
python scripts\\generate_synthetic_data.py --seed {seed} --submissions {parameters['submissions']} --flags {parameters['flags']} --cases {parameters['cases']} --verify-reproducible
```

Default full scale is 10,000 submissions, 1,000 threshold-triggered flags, and
300 cases. Smaller scale arguments use the same generator and rule logic.

## Contents

- One CSV per relational table, plus `data.json` and MySQL `seed.sql`.
- `ground_truth.csv` and `ground_truth.json` are separate evaluation labels;
  they are deliberately excluded from `data.json`, CSV input tables, and SQL.
- `data_dictionary.json` defines core entity fields, types, nullability,
  uniqueness, validation, cardinalities, lifecycle states, and effective-date
  limits of the current application model.
- `source_manifest.json` records generator version, seed, parameters, counts,
  and SHA-256 checksums.
- `validation_summary.json` reports reconciliation metrics and expected,
  explicitly labelled edge-case anomalies.

## Domain generation rules

Scores are derived from the three synthetic match components, which reconcile
to the report score. Scores 0-39 map to `INFORMATION`, 40-69 to `REVIEW`, and
70-100 to `PRIORITY_REVIEW`; only the latter two create flags. A flag is never
itself a misconduct finding. Human decision labels are generated from the
synthetic source profile and score using the documented rule in the generator;
legitimate quotation/template overlap is labelled separately and can be
appealed successfully when the synthetic reviewer makes a false-positive
decision.

The four intentionally injected issues are recorded in `ground_truth`:
`FLAG_TREATED_AS_GUILT`, `REVIEWER_CONFLICT`,
`EVIDENCE_AFTER_DECISION_WITHOUT_HISTORY`, and
`APPEAL_CLOSED_WITHOUT_INDEPENDENT_REVIEW`. They are detectable anomalies,
not silently mixed into ordinary rows.

## Relational notes

Primary keys are deterministic integers within each table. Business codes are
stable and zero-padded. Foreign keys are explicit. `case_flags` links cases and
flags; `decision_evidence` and `appeal_evidence` link existing evidence to
decision/appeal snapshots. Case and appeal event tables retain lifecycle
history. Appeals are one per decision in this data model. See
`data_dictionary.json` for entity cardinalities and effective-time details.

## Seed loading

`seed.sql` assumes the matching application tables already exist and that the
target database is empty. Load it only into a dedicated test or analytics
database. It is not a schema migration and must not be run against production.
"""
    (output_dir / "README.md").write_text(readme, encoding="utf-8", newline="\n")

    checksummed_files = sorted(
        path for path in output_dir.iterdir()
        if path.is_file() and path.name != "source_manifest.json"
    )
    manifest = {
        "generator": "scripts/generate_synthetic_data.py",
        "generator_version": GENERATOR_VERSION,
        "seed": seed,
        "parameters": parameters,
        "default_scale": {
            "submissions": 10_000,
            "flags": 1_000,
            "cases": 300,
        },
        "synthetic_only": True,
        "external_sources": [],
        "row_counts": validation["row_counts"],
        "checksums_sha256": {
            path.name: _sha256_file(path) for path in checksummed_files
        },
    }
    (output_dir / "source_manifest.json").write_bytes(_json_bytes(manifest))
    return manifest


def verify_reproducibility(
    submissions_count: int,
    flags_count: int,
    cases_count: int,
    seed: int,
) -> dict[str, Any]:
    first, first_truth = generate_dataset(
        submissions_count, flags_count, cases_count, seed
    )
    second, second_truth = generate_dataset(
        submissions_count, flags_count, cases_count, seed
    )
    first_digest = hashlib.sha256(
        _json_bytes({"tables": first, "ground_truth": first_truth})
    ).hexdigest()
    second_digest = hashlib.sha256(
        _json_bytes({"tables": second, "ground_truth": second_truth})
    ).hexdigest()
    return {
        "reproducible": first_digest == second_digest,
        "first_sha256": first_digest,
        "second_sha256": second_digest,
        "row_counts": {name: len(rows) for name, rows in first.items()},
    }


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate deterministic, linked synthetic integrity records."
    )
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--submissions", type=int, default=10_000)
    parser.add_argument("--flags", type=int, default=1_000)
    parser.add_argument("--cases", type=int, default=300)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--verify-reproducible",
        action="store_true",
        help="Generate twice in memory and compare canonical SHA-256 checksums.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        if args.verify_reproducible:
            result = verify_reproducibility(
                args.submissions, args.flags, args.cases, args.seed
            )
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0 if result["reproducible"] else 1

        tables, truth = generate_dataset(
            args.submissions,
            args.flags,
            args.cases,
            args.seed,
        )
        validation = validate_dataset(
            tables,
            truth,
            args.submissions,
            args.flags,
            args.cases,
        )
        if validation["errors"]:
            print(json.dumps(validation, indent=2, sort_keys=True), file=sys.stderr)
            return 1
        parameters = {
            "submissions": args.submissions,
            "flags": args.flags,
            "cases": args.cases,
        }
        manifest = write_exports(
            args.out,
            tables,
            truth,
            validation,
            args.seed,
            parameters,
        )
        print(json.dumps({
            "output_directory": str(args.out.resolve()),
            "status": validation["status"],
            "row_counts": validation["row_counts"],
            "metrics": validation["metrics"],
            "manifest": str((args.out / "source_manifest.json").resolve()),
            "manifest_sha256": hashlib.sha256(
                _json_bytes(manifest)
            ).hexdigest(),
        }, indent=2, sort_keys=True))
        return 0
    except (OSError, ValueError) as exc:
        print(f"Generation failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
