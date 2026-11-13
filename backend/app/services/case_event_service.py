from sqlalchemy.orm import Session
from app.models.case_event import CaseEvent

class CaseEventService:
    """
    Append-only audit service for case events.
    Guarantees immutable logging of all case lifecycle transitions and actions.
    """
    def __init__(self, db: Session):
        self.db = db

    def record_event(
        self,
        case_id: int,
        event_type: str,
        description: str,
        actor_id: int | None = None,
        actor_role: str | None = None
    ) -> CaseEvent:
        event = CaseEvent(
            case_id=case_id,
            event_type=event_type,
            description=description,
            actor_id=actor_id,
            actor_role=actor_role
        )
        self.db.add(event)
        self.db.flush()
        return event

    def get_case_events(self, case_id: int) -> list[CaseEvent]:
        return (
            self.db.query(CaseEvent)
            .filter(CaseEvent.case_id == case_id)
            .order_by(CaseEvent.created_at.asc(), CaseEvent.id.asc())
            .all()
        )

