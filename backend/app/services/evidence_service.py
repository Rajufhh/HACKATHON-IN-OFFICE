"""
EvidenceService — OOP Concept: Encapsulation + Immutability

Evidence is append-only.  Once added, an evidence item is never updated or
deleted.  If a correction is needed, a new evidence item is added with a note
explaining the correction.

This service encapsulates all evidence operations so no other layer needs to
know about the database schema.
"""

from datetime import datetime

from app.models.evidence_item import EvidenceItem


ALLOWED_EVIDENCE_TYPES = {
    "DOCUMENT",
    "SUBMISSION_VERSION",
    "EXPLANATION",
    "SIMILARITY_REPORT",
    "OTHER",
}


class EvidenceService:
    def __init__(self, db):
        self.db = db

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _generate_evidence_code(self, case_id: int) -> str:
        """Generate a case-scoped evidence code with a zero-padded sequence."""
        existing_count = (
            self.db.query(EvidenceItem)
            .filter(EvidenceItem.case_id == case_id)
            .count()
        )
        return f"EVD-{case_id:06d}-{existing_count + 1:03d}"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add_evidence(
        self,
        case_id: int,
        evidence_type: str,
        title: str,
        description: str | None = None,
        source_reference: str | None = None,
        sha256_hash: str | None = None,
        mime_type: str | None = None,
        file_size_bytes: int | None = None,
        collected_at: datetime | None = None,
        added_by: int | None = None,
    ) -> EvidenceItem:
        """
        Add a new piece of evidence to a case.

        Rules:
        - evidence_type must be one of ALLOWED_EVIDENCE_TYPES.
        - title cannot be blank.
        - No delete / update exposed by this service.
        """
        evidence_type = evidence_type.upper().strip()
        if evidence_type not in ALLOWED_EVIDENCE_TYPES:
            raise ValueError(
                f"Invalid evidence_type '{evidence_type}'. "
                f"Allowed: {sorted(ALLOWED_EVIDENCE_TYPES)}"
            )

        title = title.strip()
        if not title:
            raise ValueError("Evidence title cannot be blank.")

        item = EvidenceItem(
            evidence_code=self._generate_evidence_code(case_id),
            case_id=case_id,
            evidence_type=evidence_type,
            title=title,
            description=description,
            source_reference=source_reference,
            sha256_hash=sha256_hash,
            mime_type=mime_type,
            file_size_bytes=file_size_bytes,
            collected_at=collected_at,
            added_by=added_by,
        )
        self.db.add(item)
        self.db.flush()
        return item

    def get_case_evidence(self, case_id: int) -> list[EvidenceItem]:
        """Return all evidence items for a case, oldest first."""
        return (
            self.db.query(EvidenceItem)
            .filter(EvidenceItem.case_id == case_id)
            .order_by(EvidenceItem.added_at.asc())
            .all()
        )

    def get_evidence_by_id(self, evidence_id: int) -> EvidenceItem | None:
        return self.db.query(EvidenceItem).filter(EvidenceItem.id == evidence_id).first()

    def get_evidence_by_ids(self, evidence_ids: list[int]) -> list[EvidenceItem]:
        """Fetch a batch of evidence items by their IDs."""
        if not evidence_ids:
            return []
        return (
            self.db.query(EvidenceItem)
            .filter(EvidenceItem.id.in_(evidence_ids))
            .all()
        )

