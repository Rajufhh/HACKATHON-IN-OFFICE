from sqlalchemy.orm import Session

from app.models.appeal_event import AppealEvent


class AppealEventService:
    """Records and retrieves append-only appeal audit events."""

    def __init__(self, db: Session):
        self.db = db

    def record_event(
        self,
        appeal_id: int,
        event_type: str,
        description: str,
        actor_id: int | None = None,
        actor_role: str | None = None,
    ) -> AppealEvent:
        event = AppealEvent(
            appeal_id=appeal_id,
            event_type=event_type,
            description=description,
            actor_id=actor_id,
            actor_role=actor_role,
        )
        self.db.add(event)
        self.db.flush()
        return event

    def get_events(self, appeal_id: int) -> list[AppealEvent]:
        return (
            self.db.query(AppealEvent)
            .filter(AppealEvent.appeal_id == appeal_id)
            .order_by(AppealEvent.created_at.asc(), AppealEvent.id.asc())
            .all()
        )
