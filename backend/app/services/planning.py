from sqlalchemy.orm import Session

from app.agents.orchestrator import AgentOrchestrator
from app.models.entities import Recommendation, Scenario, TrainingPlan, User
from app.schemas.planning import PlanItem, RecommendationRead, TrainingPlanRead
from app.services.analytics import TrainingAnalyticsService


class TrainingPlanService:
    MAX_ITEMS = 3

    def __init__(self, db: Session) -> None:
        self.db = db

    async def generate(self, user: User) -> TrainingPlanRead:
        analysis = TrainingAnalyticsService(self.db).abilities(user.id)
        scenarios = self.db.query(Scenario).order_by(Scenario.id).all()
        items = self._select_items(analysis, scenarios)
        snapshot = {
            "completed_sessions": analysis.completed_sessions,
            "average_score": analysis.average_score,
            "pass_rate": analysis.pass_rate,
            "weaknesses": [item.model_dump() for item in analysis.weaknesses],
        }
        ai_generated = True
        try:
            result = await AgentOrchestrator().run(
                "planner",
                "请解释为什么安排这些训练以及执行重点。不得增删、重排场景或修改目标分。",
                {
                    "student": {"id": user.id, "display_name": user.display_name},
                    "deterministic_plan": [item.model_dump() for item in items],
                    "analysis_snapshot": snapshot,
                    "constraints": ["计划项目、顺序和目标分已由确定性分析冻结"],
                },
            )
            explanation = result.content
        except Exception:
            ai_generated = False
            explanation = "计划已依据确定性能力分析生成。请按优先级完成训练并达到目标分。"

        plan = TrainingPlan(
            user_id=user.id,
            title="个性化银行柜员训练计划",
            goals=[f"完成{item.scenario_title}并达到 {item.target_score:g} 分" for item in items],
            schedule={
                "version": 1,
                "items": [item.model_dump() for item in items],
                "planner_explanation": explanation,
                "ai_generated": ai_generated,
                "analysis_snapshot": snapshot,
            },
        )
        self.db.add(plan)
        self.db.flush()
        for item in items:
            self.db.add(
                Recommendation(
                    user_id=user.id,
                    plan_id=plan.id,
                    recommendation_type="next_training",
                    content=f"{item.scenario_title}：{item.reason}",
                    priority=item.priority,
                )
            )
        self.db.commit()
        self.db.refresh(plan)
        return self._read(plan)

    def current(self, user_id: int) -> TrainingPlanRead | None:
        plan = (
            self.db.query(TrainingPlan)
            .filter(TrainingPlan.user_id == user_id)
            .order_by(TrainingPlan.id.desc())
            .first()
        )
        return self._read(plan) if plan else None

    def history(self, user_id: int) -> list[TrainingPlanRead]:
        plans = (
            self.db.query(TrainingPlan)
            .filter(TrainingPlan.user_id == user_id)
            .order_by(TrainingPlan.id.desc())
            .all()
        )
        return [self._read(plan) for plan in plans]

    def _select_items(self, analysis, scenarios: list[Scenario]) -> list[PlanItem]:
        ability_by_type = {item.business_type: item for item in analysis.business_abilities}
        scenario_by_type = {item.business_type: item for item in scenarios}
        selected: list[tuple[Scenario, str, str, float | None]] = []

        weak = sorted(
            (item for item in analysis.business_abilities if item.average_score < 85),
            key=lambda item: (item.average_score, item.business_type),
        )
        for ability in weak:
            scenario = scenario_by_type.get(ability.business_type)
            if scenario:
                selected.append((scenario, "weak_business", f"当前平均分 {ability.average_score:g}，需优先强化。", ability.average_score))

        difficulty_rank = {"basic": 0, "intermediate": 1, "advanced": 2}
        untrained = sorted(
            (item for item in scenarios if item.business_type not in ability_by_type),
            key=lambda item: (difficulty_rank.get(item.difficulty, 9), item.id),
        )
        for scenario in untrained:
            if len(selected) >= self.MAX_ITEMS:
                break
            selected.append((scenario, "untrained_business", "尚无完成记录，建议补齐业务覆盖。", None))

        if not selected:
            mastered = sorted(
                analysis.business_abilities,
                key=lambda item: (item.average_score, item.business_type),
            )
            for ability in mastered[: self.MAX_ITEMS]:
                scenario = scenario_by_type.get(ability.business_type)
                if scenario:
                    selected.append((scenario, "reinforcement", "已达到目标，安排周期性巩固。", ability.average_score))

        result = []
        for index, (scenario, source, reason, average) in enumerate(selected[: self.MAX_ITEMS], start=1):
            target = 85.0 if average is None else min(100.0, max(85.0, average + 10))
            result.append(
                PlanItem(
                    priority=index,
                    scenario_id=scenario.id,
                    scenario_title=scenario.title,
                    business_type=scenario.business_type,
                    reason=reason,
                    source=source,
                    current_average=average,
                    target_score=round(target, 2),
                )
            )
        return result

    @staticmethod
    def _read(plan: TrainingPlan) -> TrainingPlanRead:
        schedule = plan.schedule or {}
        return TrainingPlanRead(
            id=plan.id,
            user_id=plan.user_id,
            title=plan.title,
            goals=list(plan.goals or []),
            items=[PlanItem.model_validate(item) for item in schedule.get("items", [])],
            planner_explanation=schedule.get("planner_explanation", ""),
            ai_generated=bool(schedule.get("ai_generated", False)),
            analysis_snapshot=dict(schedule.get("analysis_snapshot", {})),
            recommendations=[
                RecommendationRead(
                    id=item.id,
                    recommendation_type=item.recommendation_type,
                    content=item.content,
                    priority=item.priority,
                )
                for item in sorted(plan.recommendations, key=lambda item: (item.priority, item.id))
            ],
            created_at=plan.created_at.isoformat(),
        )
