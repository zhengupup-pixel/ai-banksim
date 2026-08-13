from app.agents.coach_agent import CoachAgent
from app.agents.customer_agent import CustomerAgent
from app.agents.examiner_agent import ExaminerAgent
from app.agents.planner_agent import PlannerAgent
from app.agents.scenario_agent import ScenarioAgent
from app.ai.providers import get_ai_provider


class AgentOrchestrator:
    def __init__(self) -> None:
        provider = get_ai_provider()
        self.agents = {
            "customer": CustomerAgent(provider),
            "coach": CoachAgent(provider),
            "examiner": ExaminerAgent(provider),
            "scenario": ScenarioAgent(provider),
            "planner": PlannerAgent(provider),
        }

    async def run(self, agent_name: str, user_prompt: str, context: dict | None = None):
        agent = self.agents.get(agent_name)
        if agent is None:
            available = ", ".join(sorted(self.agents))
            raise ValueError(f"Unknown agent '{agent_name}'. Available agents: {available}")
        return await agent.run(user_prompt, context)

