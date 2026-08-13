from typing import Literal

from pydantic import BaseModel, Field, model_validator


class RuleInput(BaseModel):
    name: str
    label: str
    input_type: Literal["text", "number"] = "text"
    required: bool = True
    minimum: float | None = None
    maximum: float | None = None


class FieldMatchRule(BaseModel):
    left_field: str
    right_field: str
    message: str = "客户信息与业务材料不匹配。"


class BalanceRule(BaseModel):
    amount_field: str = "amount"
    balance_field: str = "account_balance"
    message: str = "账户余额不足。"


class ConditionalStepRule(BaseModel):
    field: str
    operator: Literal["gte", "gt", "lte", "lt", "eq"]
    value: float | str
    required_step: str
    message: str
    before_step: str | None = None
    order_message: str | None = None


class BusinessRulePolicy(BaseModel):
    version: Literal[1] = 1
    enforce_step_order: bool = True
    inputs: list[RuleInput] = Field(default_factory=list)
    field_matches: list[FieldMatchRule] = Field(default_factory=list)
    balance_rules: list[BalanceRule] = Field(default_factory=list)
    conditional_steps: list[ConditionalStepRule] = Field(default_factory=list)
    available_steps: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_rule_references(self) -> "BusinessRulePolicy":
        input_names = {item.name for item in self.inputs}
        if len(input_names) != len(self.inputs):
            raise ValueError("Rule policy input names must be unique")
        referenced_fields = {
            field
            for rule in self.field_matches
            for field in (rule.left_field, rule.right_field)
        }
        referenced_fields.update(
            field
            for rule in self.balance_rules
            for field in (rule.amount_field, rule.balance_field)
        )
        referenced_fields.update(rule.field for rule in self.conditional_steps)
        unknown = referenced_fields - input_names
        if unknown:
            raise ValueError(f"Rule policy references undefined inputs: {', '.join(sorted(unknown))}")
        unavailable_steps = {
            rule.required_step for rule in self.conditional_steps
            if rule.required_step not in self.available_steps
        }
        if unavailable_steps:
            raise ValueError(
                f"Conditional steps must be listed in available_steps: {', '.join(sorted(unavailable_steps))}"
            )
        return self
