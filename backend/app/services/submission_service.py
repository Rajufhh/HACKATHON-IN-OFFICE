from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.models.submission import Submission
from app.models.learner import Learner
from app.models.assessment import Assessment
from app.models.similarity_report import SimilarityReport
from app.models.flag import Flag
from app.schemas.submission import SubmissionCreate
from app.services.base_service import BaseService

class SubmissionService(BaseService[Submission]):
    """
    Submission Service encapsulating submission-specific domain logic,
    validation of parent foreign keys (Learner and Assessment), and queries.
    """
    model = Submission

    def create_submission(self, data: SubmissionCreate) -> Submission:
        # Check learner exists
        learner = self.db.query(Learner).filter(Learner.id == data.learner_id).first()
        if not learner:
            raise ValueError("Learner does not exist")

        # Check assessment exists
        assessment = self.db.query(Assessment).filter(Assessment.id == data.assessment_id).first()
        if not assessment:
            raise ValueError("Assessment does not exist")

        # Create submission
        submission = Submission(
            submission_code=data.submission_code,
            learner_id=data.learner_id,
            assessment_id=data.assessment_id,
            file_reference=data.file_reference,
            content_hash=data.content_hash,
            version_number=data.version_number,
            status="SUBMITTED"
        )
        self.db.add(submission)
        try:
            self.db.commit()
            self.db.refresh(submission)
            return submission
        except IntegrityError as err:
            self.db.rollback()
            raise ValueError(f"Duplicate submission code or database error: {err.orig}")

    def get_all_submissions(self) -> list[Submission]:
        return self.db.query(Submission).all()

    def get_submission_by_id(self, submission_id: int) -> Submission | None:
        return self.db.query(Submission).filter(Submission.id == submission_id).first()

    def get_submissions_by_learner(self, learner_id: int) -> list[Submission]:
        return self.db.query(Submission).filter(Submission.learner_id == learner_id).all()

    def get_submissions_by_assessment(self, assessment_id: int) -> list[Submission]:
        return self.db.query(Submission).filter(Submission.assessment_id == assessment_id).all()

    def delete_submission(self, submission_id: int) -> bool:
        submission = self.get_submission_by_id(submission_id)
        if not submission:
            return False

        has_report = self.db.query(SimilarityReport.id).filter(
            SimilarityReport.submission_id == submission_id
        ).first()
        if has_report:
            raise ValueError(
                "Cannot delete a submission after similarity analysis; its report and review history must be preserved."
            )

        has_flag = self.db.query(Flag.id).filter(
            Flag.submission_id == submission_id
        ).first()
        if has_flag:
            raise ValueError(
                "Cannot delete a submission linked to an integrity flag or case."
            )

        self.db.delete(submission)
        try:
            self.db.commit()
        except IntegrityError as err:
            self.db.rollback()
            raise ValueError(
                "Cannot delete this submission because it is referenced by other records."
            ) from err
        return True

