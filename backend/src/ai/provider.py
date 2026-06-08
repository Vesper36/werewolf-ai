"""LLM Provider 适配层。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx


@dataclass
class AIProviderConfig:
    provider: str = "offline"
    base_url: str = "https://api.openai.com/v1"
    api_key: str = ""
    model: str = "gpt-4o-mini"
    temperature: float = 0.75
    timeout_seconds: float = 25

    @property
    def enabled(self) -> bool:
        return self.provider != "offline" and bool(self.base_url) and bool(self.model)

    def masked(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "base_url": self.base_url,
            "model": self.model,
            "temperature": self.temperature,
            "has_api_key": bool(self.api_key),
        }


class LLMClient:
    """薄封装，避免把 SDK 类型扩散到业务层。"""

    async def chat(self, config: AIProviderConfig, messages: list[dict[str, str]], max_tokens: int = 420) -> str:
        if not config.enabled:
            raise RuntimeError("AI provider is disabled")
        provider = config.provider.lower()
        if provider == "anthropic":
            return await self._anthropic_messages(config, messages, max_tokens)
        return await self._openai_compatible(config, messages, max_tokens)

    async def _openai_compatible(self, config: AIProviderConfig, messages: list[dict[str, str]], max_tokens: int) -> str:
        base_url = config.base_url.rstrip("/")
        url = f"{base_url}/chat/completions"
        headers = {"Content-Type": "application/json"}
        if config.api_key:
            headers["Authorization"] = f"Bearer {config.api_key}"
        payload = {
            "model": config.model,
            "messages": messages,
            "temperature": config.temperature,
            "max_tokens": max_tokens,
        }
        async with httpx.AsyncClient(timeout=config.timeout_seconds) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
        return data["choices"][0]["message"]["content"].strip()

    async def _anthropic_messages(self, config: AIProviderConfig, messages: list[dict[str, str]], max_tokens: int) -> str:
        base_url = config.base_url.rstrip("/")
        url = f"{base_url}/messages"
        system_parts = [m["content"] for m in messages if m["role"] == "system"]
        user_messages = [m for m in messages if m["role"] != "system"]
        headers = {
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        }
        if config.api_key:
            headers["x-api-key"] = config.api_key
        payload = {
            "model": config.model,
            "system": "\n\n".join(system_parts),
            "messages": user_messages,
            "temperature": config.temperature,
            "max_tokens": max_tokens,
        }
        async with httpx.AsyncClient(timeout=config.timeout_seconds) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
        parts = data.get("content", [])
        text_parts = [part.get("text", "") for part in parts if part.get("type") == "text"]
        return "\n".join(text_parts).strip()
