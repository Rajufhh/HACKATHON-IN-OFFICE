from app.services.base_service import BaseService
from app.models.integrity_rule import IntegrityRule

class IntegrityRuleService(BaseService[IntegrityRule]):
    """
    Integrity Rule Service inheriting standard CRUD from BaseService.
    Can evaluate similarity scores against active rules.
    """
    model = IntegrityRule

    def evaluate_similarity(self, score: float) -> str:
        """
        Evaluates a similarity score against stored rules to determine the action.
        Rules stored in MySQL take precedence:
        - 0-19: INFORMATION
        - 20-39: INFORMATION
        - 40-69: REVIEW
        - 70-100: PRIORITY_REVIEW
        """
        rules = self.db.query(IntegrityRule).order_by(IntegrityRule.min_similarity.asc()).all()
        for rule in rules:
            if rule.min_similarity <= score <= rule.max_similarity:
                return rule.action

        # Aligned fallback:
        if score >= 70:
            return "PRIORITY_REVIEW"
        elif score >= 40:
            return "REVIEW"
        return "INFORMATION"
