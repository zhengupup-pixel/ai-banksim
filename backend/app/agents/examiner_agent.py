from app.agents.base import BaseAgent


class ExaminerAgent(BaseAgent):
    name = "examiner"
    system_prompt = "你是考官 Agent，只解释表现与扣分原因，不能覆盖规则引擎结论。"

