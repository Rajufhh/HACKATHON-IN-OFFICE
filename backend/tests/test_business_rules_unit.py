from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.models.flag import Flag
from app.models.integrity_rule import IntegrityRule
from app.models.similarity_report import SimilarityReport
from app.models.submission import Submission
from app.services.appeal_lifecycle_service import AppealLifecycleService
from app.services.appeal_service import AppealService
from app.services.case_lifecycle_service import CaseLifecycleService
from app.services.integrity_rule_service import IntegrityRuleService
from app.services.reviewer_conflict_service import ReviewerConflictService
from app.services.similarity_service import SimilarityService
from app.services.analyzers.base_analyzer import AnalysisResult


@pytest.mark.parametrize(
    ("score", "expected_action"),
    [
        (0, "INFORMATION"),
        (39, "INFORMATION"),
        (40, "REVIEW"),
        (69, "REVIEW"),
        (70, "PRIORITY_REVIEW"),
        (100, "PRIORITY_REVIEW"),
    ],
)
def test_similarity_rule_threshold_boundaries(score, expected_action):
    db = Mock()
    db.query.return_value.order_by.return_value.all.return_value = []

    action = IntegrityRuleService(db).evaluate_similarity(score)

    assert action == expected_action


def test_similarity_uses_configured_integrity_rule():
    db = Mock()
    db.query.return_value.order_by.return_value.all.return_value = [
        SimpleNamespace(min_similarity=45, max_similarity=55, action="REVIEW")
    ]

    assert IntegrityRuleService(db).evaluate_similarity(50) == "REVIEW"


@pytest.mark.parametrize(
    ("score", "expected_action", "expected_flag"),
    [
        (25.0, "INFORMATION", False),
        (82.5, "PRIORITY_REVIEW", True),
    ],
)
def test_similarity_service_persists_report_and_flags_only_review_scores(
    score,
    expected_action,
    expected_flag,
):
    submission = SimpleNamespace(
        id=12,
        submission_code="SUB-2026-000012",
        file_reference=None,
    )
    matching_rule = SimpleNamespace(
        id=7,
        min_similarity=70,
        max_similarity=100,
        action="PRIORITY_REVIEW",
    )
    rules = [
        SimpleNamespace(
            min_similarity=0,
            max_similarity=39,
            action="INFORMATION",
        ),
        SimpleNamespace(
            min_similarity=40,
            max_similarity=69,
            action="REVIEW",
        ),
        matching_rule,
    ]

    def query_for(model):
        query = Mock()
        if model is Submission:
            query.filter.return_value.first.return_value = submission
        elif model is SimilarityReport:
            query.filter.return_value.count.return_value = 0
        elif model is IntegrityRule:
            query.order_by.return_value.all.return_value = rules
            query.filter.return_value.first.return_value = (
                matching_rule if expected_flag else None
            )
        elif model is Flag:
            query.count.return_value = 0
        else:
            raise AssertionError(f"Unexpected database query for {model}")
        return query

    db = Mock()
    db.query.side_effect = query_for
    analyzer = Mock()
    analyzer.analyze.return_value = AnalysisResult(
        overall_score=score,
        quotation_percentage=5.0,
        template_percentage=5.0,
        internet_percentage=score - 10.0,
    )

    result = SimilarityService(db, analyzer=analyzer).analyze_submission(12)

    assert result["report"].overall_score == score
    assert result["rule_action"] == expected_action
    assert result["flag_created"] is expected_flag
    assert (result["flag"] is not None) is expected_flag
    assert "does not establish guilt" in result["due_process_notice"]
    if expected_flag:
        assert result["flag"].integrity_rule_id == matching_rule.id
        assert result["flag"].status == "OPEN"
    else:
        assert all(not isinstance(call.args[0], Flag) for call in db.add.call_args_list)
    db.commit.assert_called_once()


@pytest.mark.parametrize(
    ("blocking_conflicts", "expected"),
    [(0, False), (1, True)],
)
def test_reviewer_conflict_service_reports_blocking_conflict(
    blocking_conflicts,
    expected,
):
    db = Mock()
    db.query.return_value.filter.return_value.count.return_value = blocking_conflicts

    result = ReviewerConflictService(db).has_blocking_conflict(
        reviewer_id=17,
        case_id=29,
    )

    assert result is expected


@pytest.mark.parametrize(
    ("current_status", "new_status"),
    [
        ("OPEN", "ASSIGNED"),
        ("ASSIGNED", "UNDER_REVIEW"),
        ("UNDER_REVIEW", "DECISION_PENDING"),
        ("DECISION_PENDING", "CLOSED"),
    ],
)
def test_case_lifecycle_accepts_each_sequential_transition(current_status, new_status):
    assert CaseLifecycleService().validate_transition(current_status, new_status) is True


@pytest.mark.parametrize(
    ("current_status", "new_status"),
    [
        ("OPEN", "CLOSED"),
        ("OPEN", "UNDER_REVIEW"),
        ("CLOSED", "OPEN"),
    ],
)
def test_case_lifecycle_rejects_invalid_transition(current_status, new_status):
    with pytest.raises(
        ValueError,
        match=f"Invalid case transition: {current_status} -> {new_status}",
    ):
        CaseLifecycleService().validate_transition(current_status, new_status)


def test_appeal_lifecycle_requires_review_before_decision():
    appeal = SimpleNamespace(status="SUBMITTED")

    with pytest.raises(ValueError, match="SUBMITTED -> DECIDED"):
        AppealLifecycleService().transition(appeal, "DECIDED")

    assert appeal.status == "SUBMITTED"


def test_appeal_resolution_requires_the_assigned_independent_reviewer():
    db = Mock()
    service = AppealService(db)
    appeal = SimpleNamespace(
        id=8,
        status="UNDER_REVIEW",
        assigned_reviewer_id=21,
        outcome=None,
        outcome_rationale=None,
        resolved_at=None,
    )
    service.get_appeal = Mock(return_value=appeal)
    service.events.record_event = Mock()

    with pytest.raises(ValueError, match="assigned independent reviewer"):
        service.resolve_appeal(
            appeal_id=8,
            reviewer_id=13,
            outcome="UPHELD",
            rationale="The original decision is supported by the evidence.",
        )

    assert appeal.status == "UNDER_REVIEW"
    assert appeal.outcome is None
    service.events.record_event.assert_not_called()
    db.flush.assert_not_called()


@pytest.mark.parametrize("outcome", ["UPHELD", "OVERTURNED", "REMANDED"])
def test_assigned_independent_reviewer_can_resolve_appeal(outcome):
    db = Mock()
    service = AppealService(db)
    appeal = SimpleNamespace(
        id=8,
        status="UNDER_REVIEW",
        assigned_reviewer_id=21,
        outcome=None,
        outcome_rationale=None,
        resolved_at=None,
    )
    service.get_appeal = Mock(return_value=appeal)
    service.events.record_event = Mock()

    resolved = service.resolve_appeal(
        appeal_id=8,
        reviewer_id=21,
        outcome=outcome.lower(),
        rationale="The independent reviewer considered the complete case record.",
    )

    assert resolved is appeal
    assert appeal.status == "DECIDED"
    assert appeal.outcome == outcome
    assert appeal.outcome_rationale == (
        "The independent reviewer considered the complete case record."
    )
    assert appeal.resolved_at is not None
    service.events.record_event.assert_called_once()
    assert service.events.record_event.call_args.kwargs["actor_role"] == (
        "INDEPENDENT_REVIEWER"
    )
    db.flush.assert_called_once()


def test_appeal_lifecycle_rejects_transition_after_decision():
    appeal = SimpleNamespace(status="DECIDED")

    with pytest.raises(ValueError, match="DECIDED -> WITHDRAWN"):
        AppealLifecycleService().transition(appeal, "WITHDRAWN")

    assert appeal.status == "DECIDED"
