from app.models.appeal import Appeal


class AppealLifecycleService:
    """Validates appeal status transitions."""

    VALID_TRANSITIONS = {
        "SUBMITTED": {"UNDER_REVIEW", "WITHDRAWN"},
        "UNDER_REVIEW": {"DECIDED"},
        "DECIDED": set(),
        "WITHDRAWN": set(),
    }

    def transition(self, appeal: Appeal, new_status: str) -> Appeal:
        allowed = self.VALID_TRANSITIONS.get(appeal.status, set())
        if new_status not in allowed:
            raise ValueError(
                f"Invalid appeal transition: {appeal.status} -> {new_status}"
            )
        appeal.status = new_status
        return appeal
