from app.agents.base import BaseAgent


class PlannerAgent(BaseAgent):
    name = "planner"
    system_prompt = (
        "你是银行柜员训练 PlannerAgent。计划项目、顺序、原因数据和目标分已经由确定性能力分析冻结。"
        "你只能用自然语言解释计划重点，不得增删或重排项目，不得修改目标分，不得重算历史成绩。"
    )
