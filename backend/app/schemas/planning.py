from pydantic import BaseModel


class PlanItem(BaseModel):
    priority: int
    scenario_id: int
    scenario_title: str
    business_type: str
    reason: str
    source: str
    current_average: float | None
    target_score: float


class RecommendationRead(BaseModel):
    id: int
    recommendation_type: str
    content: str
    priority: int


class TrainingPlanRead(BaseModel):
    id: int
    user_id: int
    title: str
    goals: list[str]
    items: list[PlanItem]
    planner_explanation: str
    ai_generated: bool
    analysis_snapshot: dict
    recommendations: list[RecommendationRead]
    created_at: str
