from pydantic import BaseModel, Field

from app.schemas.rules import BusinessRulePolicy
from app.schemas.conversation import PublicCustomerProfile


class ScenarioRead(BaseModel):
    id: int
    title: str
    business_type: str
    difficulty: str
    description: str
    expected_steps: list[str]
    risk_rules: dict
    rule_policy: BusinessRulePolicy
    customer_profile: PublicCustomerProfile

    model_config = {"from_attributes": True}


class ScenarioUpdate(BaseModel):
    title: str = Field(min_length=2, max_length=160)
    business_type: str = Field(min_length=2, max_length=64)
    difficulty: str = Field(pattern="^(basic|intermediate|advanced)$")
    description: str = Field(min_length=5)
    expected_steps: list[str] = Field(min_length=1)
    risk_rules: dict = Field(default_factory=dict)
    scoring_policy: dict = Field(default_factory=dict)
    rule_policy: BusinessRulePolicy
    customer_profile: PublicCustomerProfile


class ScenarioVersionRead(BaseModel):
    id: int
    scenario_id: int
    version_number: int
    changed_by_user_id: int
    snapshot: dict
    created_at: str


class TrainingSessionCreate(BaseModel):
    scenario_id: int


class TrainingSessionRead(BaseModel):
    id: int
    user_id: int
    scenario_id: int
    status: str
    context: dict

    model_config = {"from_attributes": True}


class TrainingActionCreate(BaseModel):
    action_type: str
    payload: dict = Field(default_factory=dict)


class RuleCheckResult(BaseModel):
    passed: bool
    score: float
    missing_steps: list[str]
    violations: list[str]
    suggestions: list[str]


class FinalTrainingReport(BaseModel):
    session_id: int
    status: str
    completed_at: str
    passed: bool
    rule_score: float
    total_score: float
    missing_steps: list[str]
    violations: list[str]
    suggestions: list[str]
    examiner_report: str


class TrainingHistoryItem(BaseModel):
    session_id: int
    scenario_id: int
    scenario_title: str
    business_type: str
    difficulty: str
    status: str
    started_at: str
    completed_at: str | None
    total_score: float | None
    rule_score: float | None
    passed: bool | None


class StoredTrainingReport(FinalTrainingReport):
    user_id: int
    scenario_id: int
    scenario_title: str
    business_type: str
    difficulty: str
    started_at: str


class BusinessAbility(BaseModel):
    business_type: str
    scenario_title: str
    completed_count: int
    average_score: float
    pass_rate: float
    level: str


class WeaknessCategory(BaseModel):
    category: str
    count: int


class AbilityAnalysis(BaseModel):
    user_id: int
    completed_sessions: int
    average_score: float
    pass_rate: float
    business_abilities: list[BusinessAbility]
    weaknesses: list[WeaknessCategory]
    recommended_business_types: list[str]


class AIEvaluationRequest(BaseModel):
    session_id: int
    learner_message: str
    agent_name: str = "coach"


class AIEvaluationResponse(BaseModel):
    agent_name: str
    content: str
    metadata: dict = Field(default_factory=dict)
