import pytest

from app.schemas.rules import BusinessRulePolicy
from app.services.demo_scenarios import DEMO_SCENARIOS
from app.services.rule_engine import BusinessRuleEngine


VALID_CONTEXTS = {
    "account_opening": {"presented_id_number": "ID001", "customer_id_number": "ID001"},
    "deposit": {"amount": 60000, "account_number": "A001", "customer_account_number": "A001"},
    "withdrawal": {
        "amount": 60000, "account_balance": 80000,
        "presented_id_number": "ID001", "customer_id_number": "ID001",
    },
    "transfer": {
        "amount": 120000, "account_balance": 200000,
        "payer_id_number": "ID001", "account_owner_id_number": "ID001",
        "recipient_account": "A002",
    },
    "loss_reporting": {
        "card_number": "C001", "presented_id_number": "ID001", "card_owner_id_number": "ID001",
    },
    "card_replacement": {
        "loss_report_number": "L001", "presented_id_number": "ID001",
        "card_owner_id_number": "ID001", "replacement_fee": 10,
    },
}


@pytest.mark.parametrize("scenario", DEMO_SCENARIOS, ids=lambda item: item["business_type"])
def test_all_demo_scenario_policies_accept_valid_workflow(scenario: dict) -> None:
    policy = BusinessRulePolicy.model_validate(scenario["rule_policy"])
    performed_steps = list(scenario["expected_steps"])
    for rule in policy.conditional_steps:
        insertion_index = performed_steps.index(rule.before_step) if rule.before_step else len(performed_steps)
        performed_steps.insert(insertion_index, rule.required_step)

    result = BusinessRuleEngine().evaluate(
        scenario["expected_steps"],
        performed_steps,
        VALID_CONTEXTS[scenario["business_type"]],
        scenario["rule_policy"],
    )

    assert result.passed is True
    assert result.score == 100


def test_rule_engine_rejects_out_of_order_operations() -> None:
    scenario = DEMO_SCENARIOS[0]
    performed_steps = list(scenario["expected_steps"])
    performed_steps[0], performed_steps[1] = performed_steps[1], performed_steps[0]

    result = BusinessRuleEngine().evaluate(
        scenario["expected_steps"], performed_steps, VALID_CONTEXTS["account_opening"], scenario["rule_policy"]
    )

    assert result.passed is False
    assert "柜面操作顺序不符合规定业务流程。" in result.violations


def test_withdrawal_rejects_insufficient_balance_identity_mismatch_and_missing_authorization() -> None:
    scenario = DEMO_SCENARIOS[2]
    context = {
        "amount": 60000, "account_balance": 50000,
        "presented_id_number": "ID-WRONG", "customer_id_number": "ID001",
    }

    result = BusinessRuleEngine().evaluate(
        scenario["expected_steps"], scenario["expected_steps"], context, scenario["rule_policy"]
    )

    assert result.passed is False
    assert "取款金额超过账户可用余额。" in result.violations
    assert "取款人身份与账户登记身份不匹配。" in result.violations
    assert "大额取款缺少主管授权。" in result.violations


def test_transfer_rejects_invalid_amount_and_unknown_operation() -> None:
    scenario = DEMO_SCENARIOS[3]
    context = {**VALID_CONTEXTS["transfer"], "amount": -1}

    result = BusinessRuleEngine().evaluate(
        scenario["expected_steps"],
        [*scenario["expected_steps"], "override_rule_engine"],
        context,
        scenario["rule_policy"],
    )

    assert result.passed is False
    assert "转账金额不能低于 0.01。" in result.violations
    assert "场景不允许执行操作：override_rule_engine。" in result.violations


def test_large_transfer_authorization_after_execution_is_rejected() -> None:
    scenario = DEMO_SCENARIOS[3]
    performed_steps = [*scenario["expected_steps"], "authorize_large_transfer"]

    result = BusinessRuleEngine().evaluate(
        scenario["expected_steps"], performed_steps, VALID_CONTEXTS["transfer"], scenario["rule_policy"]
    )

    assert result.passed is False
    assert "大额转账授权必须在转账执行前完成。" in result.violations
