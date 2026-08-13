from app.agents.base import BaseAgent


class CoachAgent(BaseAgent):
    name = "coach"
    system_prompt = "你是银行柜员训练教练，给出过程性提醒，避免直接给最终答案。"

