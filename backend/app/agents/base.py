from dataclasses import dataclass

from app.ai.providers import AIProvider


@dataclass(frozen=True)
class AgentResult:
    agent_name: str
    content: str
    metadata: dict


class BaseAgent:
    name = "base"
    system_prompt = "你是 AI BankSim 的通用训练助手。"

    def __init__(self, provider: AIProvider) -> None:
        self.provider = provider

    async def run(self, user_prompt: str, context: dict | None = None) -> AgentResult:
        context = context or {}
        content = await self.provider.complete(self.system_prompt, self._build_prompt(user_prompt, context))
        return AgentResult(agent_name=self.name, content=content, metadata={"context": context})

    def _build_prompt(self, user_prompt: str, context: dict) -> str:
        return f"训练上下文：{context}\n用户输入：{user_prompt}"

