from app.agents.base import BaseAgent


class ScenarioAgent(BaseAgent):
    name = "scenario"
    system_prompt = "你负责生成银行柜面训练场景草案，必须输出可被规则引擎校验的步骤。"

