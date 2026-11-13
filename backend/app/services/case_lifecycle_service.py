class CaseLifecycleService:
    """
    Enforces valid state machine transitions for academic integrity cases.
    Transitions:
    OPEN -> ASSIGNED -> UNDER_REVIEW -> DECISION_PENDING -> CLOSED
    """
    ALLOWED_TRANSITIONS = {
        "OPEN": {"ASSIGNED"},
        "ASSIGNED": {"UNDER_REVIEW"},
        "UNDER_REVIEW": {"DECISION_PENDING"},
        "DECISION_PENDING": {"CLOSED"},
        "CLOSED": set(),
    }

    def validate_transition(self, current_status: str, new_status: str) -> bool:
        allowed = self.ALLOWED_TRANSITIONS.get(current_status, set())
        if new_status not in allowed:
            raise ValueError(
                f"Invalid case transition: {current_status} -> {new_status}"
            )
        return True

