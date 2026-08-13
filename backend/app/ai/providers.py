from abc import ABC, abstractmethod

import httpx

from app.core.config import Settings, get_settings


class AIProvider(ABC):
    @abstractmethod
    async def complete(self, system_prompt: str, user_prompt: str) -> str:
        raise NotImplementedError


class MockProvider(AIProvider):
    async def complete(self, system_prompt: str, user_prompt: str) -> str:
        if "场景客户 Agent" in system_prompt:
            return "【模拟客户】好的，我会按实际情况回答。请问需要我先提供什么资料？"
        return (
            "【Mock AI】我会根据当前训练目标给出提示：先核验身份与业务材料，"
            "再按柜面流程完成操作，并注意风险复核。"
        )


class DeepSeekProvider(AIProvider):
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    async def complete(self, system_prompt: str, user_prompt: str) -> str:
        if not self.settings.deepseek_api_key:
            raise RuntimeError("DEEPSEEK_API_KEY is required when AI_PROVIDER=deepseek")

        payload = {
            "model": self.settings.deepseek_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.3,
        }
        headers = {"Authorization": f"Bearer {self.settings.deepseek_api_key}"}
        async with httpx.AsyncClient(base_url=self.settings.deepseek_base_url, timeout=30) as client:
            response = await client.post("/chat/completions", json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]


def get_ai_provider() -> AIProvider:
    settings = get_settings()
    if settings.ai_provider.lower() == "deepseek":
        return DeepSeekProvider(settings)
    return MockProvider()
