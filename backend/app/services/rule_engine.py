from dataclasses import dataclass

from pydantic import ValidationError

from app.schemas.rules import BusinessRulePolicy, ConditionalStepRule


@dataclass(frozen=True)
class RuleCheck:
    passed: bool
    score: float
    missing_steps: list[str]
    violations: list[str]
    suggestions: list[str]


class BusinessRuleEngine:
    """Deterministic business validation. AI must not override these facts."""

    def evaluate(
        self,
        expected_steps: list[str],
        performed_steps: list[str],
        context: dict,
        policy_data: dict | None = None,
    ) -> RuleCheck:
        missing_steps = [step for step in expected_steps if step not in performed_steps]
        violations: list[str] = []
        suggestions: list[str] = []

        try:
            policy = BusinessRulePolicy.model_validate(policy_data or {})
        except ValidationError:
            return RuleCheck(
                passed=False,
                score=0,
                missing_steps=missing_steps,
                violations=["场景业务规则策略配置无效，请联系教师或管理员。"],
                suggestions=["修复场景规则策略后重新开始训练。"],
            )

        if missing_steps:
            suggestions.append("按业务流程补全缺失步骤后再提交。")

        if policy.enforce_step_order:
            expected_positions = {step: index for index, step in enumerate(expected_steps)}
            performed_positions = [expected_positions[step] for step in performed_steps if step in expected_positions]
            if performed_positions != sorted(performed_positions):
                violations.append("柜面操作顺序不符合规定业务流程。")

        allowed_steps = set(expected_steps) | set(policy.available_steps)
        if unknown_steps := [step for step in performed_steps if step not in allowed_steps]:
            violations.append(f"场景不允许执行操作：{'、'.join(unknown_steps)}。")

        for rule_input in policy.inputs:
            value = context.get(rule_input.name)
            if rule_input.required and (value is None or value == ""):
                violations.append(f"缺少必填业务信息：{rule_input.label}。")
                continue
            if value is None or value == "" or rule_input.input_type != "number":
                continue
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                violations.append(f"{rule_input.label}必须为有效数字。")
                continue
            if rule_input.minimum is not None and value < rule_input.minimum:
                violations.append(f"{rule_input.label}不能低于 {rule_input.minimum:g}。")
            if rule_input.maximum is not None and value > rule_input.maximum:
                violations.append(f"{rule_input.label}不能超过 {rule_input.maximum:g}。")

        for match_rule in policy.field_matches:
            left = context.get(match_rule.left_field)
            right = context.get(match_rule.right_field)
            if left not in (None, "") and right not in (None, "") and left != right:
                violations.append(match_rule.message)

        for balance_rule in policy.balance_rules:
            amount = context.get(balance_rule.amount_field)
            balance = context.get(balance_rule.balance_field)
            if self._is_number(amount) and self._is_number(balance) and amount > balance:
                violations.append(balance_rule.message)

        for conditional_rule in policy.conditional_steps:
            if self._condition_matches(context.get(conditional_rule.field), conditional_rule):
                if conditional_rule.required_step not in performed_steps:
                    violations.append(conditional_rule.message)
                elif conditional_rule.before_step and conditional_rule.before_step in performed_steps:
                    if performed_steps.index(conditional_rule.required_step) > performed_steps.index(conditional_rule.before_step):
                        violations.append(
                            conditional_rule.order_message
                            or f"{conditional_rule.required_step} 必须在 {conditional_rule.before_step} 前完成。"
                        )

        if "amount" not in {item.name for item in policy.inputs}:
            amount = context.get("amount")
            if self._is_number(amount) and amount < 0:
                violations.append("交易金额不能为负数。")

        risk_flags = context.get("risk_flags", [])
        if "large_cash_without_review" in risk_flags:
            violations.append("大额现金业务缺少复核或授权。")

        total_required = max(len(expected_steps), 1)
        completion_score = (total_required - len(missing_steps)) / total_required * 100
        penalty = len(set(violations)) * 15
        score = max(0, round(completion_score - penalty, 2))

        return RuleCheck(
            passed=not missing_steps and not violations,
            score=score,
            missing_steps=missing_steps,
            violations=list(dict.fromkeys(violations)),
            suggestions=suggestions,
        )

    @staticmethod
    def _is_number(value: object) -> bool:
        return isinstance(value, (int, float)) and not isinstance(value, bool)

    def _condition_matches(self, actual: object, rule: ConditionalStepRule) -> bool:
        if actual is None:
            return False
        if rule.operator in {"gte", "gt", "lte", "lt"}:
            if not self._is_number(actual) or not self._is_number(rule.value):
                return False
            operations = {
                "gte": lambda: actual >= rule.value,
                "gt": lambda: actual > rule.value,
                "lte": lambda: actual <= rule.value,
                "lt": lambda: actual < rule.value,
            }
            return operations[rule.operator]()
        return actual == rule.value
