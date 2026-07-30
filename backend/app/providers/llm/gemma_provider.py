from __future__ import annotations

from typing import Any

import httpx

from app.core.config import GEMMA_MODEL, OPENROUTER_API_KEY, SITE_URL
from app.providers.base import ChatResult, LLMProvider, ProviderNotConfigured


class GemmaProvider(LLMProvider):
    name = "gemma"

    def __init__(self, model: str | None = None):
        self.model = model or GEMMA_MODEL
        if not OPENROUTER_API_KEY:
            raise ProviderNotConfigured("OPENROUTER_API_KEY is not set")

    def chat(
        self,
        messages: list[dict[str, Any]],
        *,
        system_prompt: str | None = None,
        temperature: float = 0.7,
    ) -> ChatResult:
        payload_messages: list[dict[str, Any]] = []
        if system_prompt:
            payload_messages.append({"role": "system", "content": system_prompt})
        payload_messages.extend(messages)

        response = httpx.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": SITE_URL,
                "X-Title": "AI Booth Generator",
            },
            json={
                "model": self.model,
                "messages": payload_messages,
                "temperature": temperature,
            },
            timeout=90.0,
        )

        if response.status_code != 200:
            raise RuntimeError(
                f"Gemma/OpenRouter error ({response.status_code}): {response.text[:500]}"
            )

        data = response.json()
        message = data["choices"][0]["message"]
        return ChatResult(
            content=(message.get("content") or "").strip(),
            raw=data,
            reasoning_details=message.get("reasoning_details"),
        )


class ClaudeProvider(LLMProvider):
    name = "claude"

    def chat(
        self,
        messages: list[dict[str, Any]],
        *,
        system_prompt: str | None = None,
        temperature: float = 0.7,
    ) -> ChatResult:
        raise ProviderNotConfigured(
            "ClaudeProvider is not configured yet. Set LLM_PROVIDER=gemma for development."
        )
