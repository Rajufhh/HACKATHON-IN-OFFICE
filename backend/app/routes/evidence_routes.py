from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.schemas.evidence import EvidenceCreate, EvidenceResponse
from app.services.evidence_service import EvidenceService

router = APIRouter(prefix="/evidence", tags=["Evidence"])


@router.post("/", response_model=EvidenceResponse, status_code=201)
def add_evidence(payload: EvidenceCreate, db: Session = Depends(get_db)):
    """Add a new piece of evidence to a case (append-only)."""
    svc = EvidenceService(db)
    try:
        item = svc.add_evidence(
            case_id=payload.case_id,
            evidence_type=payload.evidence_type,
            title=payload.title,
            description=payload.description,
            source_reference=payload.source_reference,
            sha256_hash=payload.sha256_hash,
            mime_type=payload.mime_type,
            file_size_bytes=payload.file_size_bytes,
            collected_at=payload.collected_at,
            added_by=payload.added_by,
        )
        db.commit()
        db.refresh(item)
        return item
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc))


@router.get("/case/{case_id}", response_model=list[EvidenceResponse])
def list_case_evidence(case_id: int, db: Session = Depends(get_db)):
    """Return all evidence items for a case."""
    svc = EvidenceService(db)
    return svc.get_case_evidence(case_id)


@router.get("/{evidence_id}", response_model=EvidenceResponse)
def get_evidence(evidence_id: int, db: Session = Depends(get_db)):
    """Return a single evidence item by ID."""
    svc = EvidenceService(db)
    item = svc.get_evidence_by_id(evidence_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"Evidence {evidence_id} not found.")
    return item

