from sqlalchemy.orm import Session
from app.models.submission import Submission
from app.models.similarity_report import SimilarityReport
from app.models.similarity_match import SimilarityMatch
from app.models.flag import Flag
from app.models.integrity_rule import IntegrityRule
from app.services.integrity_rule_service import IntegrityRuleService
from app.services.analyzers.base_analyzer import SimilarityAnalyzer
from app.services.analyzers.demo_analyzer import DemoSimilarityAnalyzer

class SimilarityService:
    """
    Coordinates similarity analysis, matching source persistence,
    and due-process flag creation using OOP Composition and Polymorphic Analyzers.
    """

    def __init__(self, db: Session, analyzer: SimilarityAnalyzer | None = None):
        self.db = db
        # Polymorphism: accepts any subclass of SimilarityAnalyzer
        self.analyzer = analyzer or DemoSimilarityAnalyzer()
        self.rule_service = IntegrityRuleService(db)

    def analyze_submission(self, submission_id: int) -> dict:
        submission = self.db.query(Submission).filter(Submission.id == submission_id).first()
        if not submission:
            raise ValueError(f"Submission with ID {submission_id} does not exist")

        # 1. Run polymorphic analyzer
        analysis = self.analyzer.analyze(
            submission_id=submission.id,
            submission_code=submission.submission_code,
            file_reference=submission.file_reference
        )

        # 2. Determine report code from the stable submission ID.
        existing_reports_count = self.db.query(SimilarityReport).filter(
            SimilarityReport.submission_id == submission_id
        ).count()
        report_code = f"SIM-{submission.id:06d}-{existing_reports_count + 1:02d}"

        # 3. Create and persist SimilarityReport
        report = SimilarityReport(
            report_code=report_code,
            submission_id=submission.id,
            overall_score=analysis.overall_score,
            quotation_percentage=analysis.quotation_percentage,
            template_percentage=analysis.template_percentage,
            internet_percentage=analysis.internet_percentage,
            status="COMPLETED"
        )
        self.db.add(report)
        self.db.flush()

        # 4. Create and persist SimilarityMatch records
        for m in analysis.matches:
            match_row = SimilarityMatch(
                report_id=report.id,
                source_type=m.source_type,
                source_reference=m.source_reference,
                matched_percentage=m.matched_percentage,
                description=m.description
            )
            self.db.add(match_row)

        # 5. Evaluate against Integrity Rules
        rule_action = self.rule_service.evaluate_similarity(analysis.overall_score)

        # Find matching IntegrityRule record in DB
        matching_rule = self.db.query(IntegrityRule).filter(
            IntegrityRule.min_similarity <= int(analysis.overall_score),
            IntegrityRule.max_similarity >= int(analysis.overall_score)
        ).first()

        flag_record = None
        flag_created = False

        # 6. Flag creation condition: Only if review or priority review is required
        if rule_action in ["REVIEW", "PRIORITY_REVIEW"]:
            if not matching_rule:
                raise ValueError(
                    f"No integrity rule covers similarity score {analysis.overall_score}."
                )
            existing_flags_count = self.db.query(Flag).count()
            flag_code = f"FLG-2026-{existing_flags_count + 1:06d}"

            flag_record = Flag(
                flag_code=flag_code,
                submission_id=submission.id,
                report_id=report.id,
                integrity_rule_id=matching_rule.id,
                flag_type=rule_action,
                status="OPEN",
                reason=(
                    f"Overall similarity of {analysis.overall_score}% triggers {rule_action}. "
                    f"Quota: {analysis.quotation_percentage}%, Template: {analysis.template_percentage}%, "
                    f"Internet: {analysis.internet_percentage}%. Human due process review required."
                )
            )
            self.db.add(flag_record)
            flag_created = True

        self.db.commit()
        self.db.refresh(report)
        if flag_record:
            self.db.refresh(flag_record)

        return {
            "report": report,
            "rule_action": rule_action,
            "flag_created": flag_created,
            "flag": flag_record,
            "due_process_notice": (
                "A similarity flag triggers human evaluation and does not establish guilt. "
                "Legitimate quotation and authorized templates are taken into account."
            )
        }

    def get_reports_by_submission(self, submission_id: int) -> list[SimilarityReport]:
        return self.db.query(SimilarityReport).filter(
            SimilarityReport.submission_id == submission_id
        ).order_by(SimilarityReport.id.desc()).all()

    def get_all_flags(self, status: str | None = None) -> list[Flag]:
        query = self.db.query(Flag)
        if status:
            query = query.filter(Flag.status == status)
        return query.order_by(Flag.id.desc()).all()

    def get_flag_by_id(self, flag_id: int) -> Flag | None:
        return self.db.query(Flag).filter(Flag.id == flag_id).first()

