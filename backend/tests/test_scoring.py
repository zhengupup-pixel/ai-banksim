from app.services.rule_engine import RuleCheck
from app.services.scoring import ScoringEngine


def test_rule_score_is_total_when_ai_only_explains() -> None:
    rule_check = RuleCheck(True, 100, [], [], [])

    result = ScoringEngine().calculate_total(
        rule_check,
        scoring_policy={"rule_weight": 0.8, "ai_weight": 0.2},
    )

    assert result["total_score"] == 100
    assert result["ai_score"] == 0
    assert result["details"]["score_source"] == "business_rule_engine"


def test_explicit_ai_rubric_score_uses_scenario_weights() -> None:
    rule_check = RuleCheck(True, 90, [], [], [])

    result = ScoringEngine().calculate_total(
        rule_check,
        ai_score=70,
        scoring_policy={"rule_weight": 0.75, "ai_weight": 0.25},
    )

    assert result["total_score"] == 85
    assert result["rule_score"] == 90
    assert result["ai_score"] == 70
