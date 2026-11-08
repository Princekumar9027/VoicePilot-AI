from abc import ABC, abstractmethod

import httpx

from app.core.config import get_settings


class LLMError(Exception):
    pass


class LLMProvider(ABC):
    @abstractmethod
    def chat(self, messages: list[dict], tools: list[dict] | None, temperature: float) -> dict:
        ...


class OpenAICompatibleProvider(LLMProvider):
    def __init__(self, api_key: str, base_url: str, model: str):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model

    def chat(self, messages: list[dict], tools: list[dict] | None, temperature: float = 0.3) -> dict:
        body: dict = {"model": self.model, "messages": messages, "temperature": temperature}
        if tools:
            body["tools"] = tools
        try:
            response = httpx.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=body,
                timeout=90,
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]
        except httpx.HTTPStatusError as exc:
            raise LLMError(f"LLM provider returned {exc.response.status_code}")
        except (httpx.HTTPError, KeyError, ValueError):
            raise LLMError("LLM provider is unreachable")


def get_llm_provider() -> LLMProvider | None:
    settings = get_settings()
    if not settings.llm_api_key:
        return None
    return OpenAICompatibleProvider(settings.llm_api_key, settings.llm_base_url, settings.llm_model)
