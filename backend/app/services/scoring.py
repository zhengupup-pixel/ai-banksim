from app.services.rule_engine import RuleCheck


class ScoringEngine:
    def calculate_total(
        self,
        rule_check: RuleCheck,
        ai_score: float | None = None,
        scoring_policy: dict | None = None,
    ) -> dict:
        policy = scoring_policy or {}
        rule_weight = float(policy.get("rule_weight", 0.8))
        ai_weight = float(policy.get("ai_weight", 0.2))

        # Until a dedicated, bounded AI rubric exists, AI explains the result but
        # does not lower the deterministic score merely because no AI score exists.
        if ai_score is None:
            total_score = rule_check.score
            stored_ai_score = 0.0
        else:
            total_score = round(rule_check.score * rule_weight + ai_score * ai_weight, 2)
            stored_ai_score = ai_score

        return {
            "total_score": total_score,
            "rule_score": rule_check.score,
            "ai_score": stored_ai_score,
            "details": {
                "missing_steps": rule_check.missing_steps,
                "violations": rule_check.violations,
                "suggestions": rule_check.suggestions,
                "score_source": "business_rule_engine" if ai_score is None else "business_rule_engine_and_ai_rubric",
            },
        }
