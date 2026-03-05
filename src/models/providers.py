"""Multi-model API provider integrations.

Each provider wraps a different AI model API. Different training distributions =
different "lived experience" = different failure modes. That diversity is the value.
"""

from __future__ import annotations

import json
import logging
import os
from abc import ABC, abstractmethod
from typing import Any, Optional

import httpx
from pydantic import BaseModel

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 120.0


class ModelResponse(BaseModel):
    """Standardized response from any model provider."""

    model: str
    provider: str
    content: str
    raw: Optional[dict[str, Any]] = None
    usage: Optional[dict[str, int]] = None


class ModelProvider(ABC):
    """Base class for AI model API providers."""

    def __init__(self, api_key: Optional[str] = None, timeout: float = DEFAULT_TIMEOUT):
        self.api_key = api_key
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @property
    @abstractmethod
    def model_id(self) -> str:
        ...

    @property
    @abstractmethod
    def role(self) -> str:
        ...

    @abstractmethod
    async def generate(self, prompt: str, system: Optional[str] = None) -> ModelResponse:
        ...

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()


class AnthropicProvider(ModelProvider):
    """Claude — foundation builder."""

    BASE_URL = "https://api.anthropic.com/v1/messages"

    def __init__(self, api_key: Optional[str] = None, model: str = "claude-sonnet-4-20250514"):
        super().__init__(api_key or os.getenv("ANTHROPIC_API_KEY"))
        self._model = model

    @property
    def name(self) -> str:
        return "claude"

    @property
    def model_id(self) -> str:
        return self._model

    @property
    def role(self) -> str:
        return "PRIMARY — checks own work, foundation builder"

    async def generate(self, prompt: str, system: Optional[str] = None) -> ModelResponse:
        client = await self._get_client()
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        body: dict[str, Any] = {
            "model": self._model,
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            body["system"] = system

        resp = await client.post(self.BASE_URL, headers=headers, json=body)
        resp.raise_for_status()
        data = resp.json()
        content = data["content"][0]["text"]
        return ModelResponse(
            model=self._model,
            provider=self.name,
            content=content,
            raw=data,
            usage=data.get("usage"),
        )


class OpenAIProvider(ModelProvider):
    """GPT — stress test, different training bias."""

    BASE_URL = "https://api.openai.com/v1/chat/completions"

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o"):
        super().__init__(api_key or os.getenv("OPENAI_API_KEY"))
        self._model = model

    @property
    def name(self) -> str:
        return "gpt"

    @property
    def model_id(self) -> str:
        return self._model

    @property
    def role(self) -> str:
        return "STRESS TEST — different training distribution, no Anthropic bias"

    async def generate(self, prompt: str, system: Optional[str] = None) -> ModelResponse:
        client = await self._get_client()
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        body = {"model": self._model, "messages": messages, "max_tokens": 4096}
        resp = await client.post(self.BASE_URL, headers=headers, json=body)
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        return ModelResponse(
            model=self._model,
            provider=self.name,
            content=content,
            raw=data,
            usage=data.get("usage"),
        )


class XAIProvider(ModelProvider):
    """Grok — adversarial reviewer, tries to destroy claims."""

    BASE_URL = "https://api.x.ai/v1/chat/completions"

    def __init__(self, api_key: Optional[str] = None, model: str = "grok-3"):
        super().__init__(api_key or os.getenv("XAI_API_KEY"))
        self._model = model

    @property
    def name(self) -> str:
        return "grok"

    @property
    def model_id(self) -> str:
        return self._model

    @property
    def role(self) -> str:
        return "ADVERSARY — contrarian, tries to destroy claims"

    async def generate(self, prompt: str, system: Optional[str] = None) -> ModelResponse:
        client = await self._get_client()
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        body = {"model": self._model, "messages": messages, "max_tokens": 4096}
        resp = await client.post(self.BASE_URL, headers=headers, json=body)
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        return ModelResponse(
            model=self._model,
            provider=self.name,
            content=content,
            raw=data,
            usage=data.get("usage"),
        )


class DeepSeekProvider(ModelProvider):
    """DeepSeek — non-Western training data, different cultural lens."""

    BASE_URL = "https://api.deepseek.com/v1/chat/completions"

    def __init__(self, api_key: Optional[str] = None, model: str = "deepseek-chat"):
        super().__init__(api_key or os.getenv("DEEPSEEK_API_KEY"))
        self._model = model

    @property
    def name(self) -> str:
        return "deepseek"

    @property
    def model_id(self) -> str:
        return self._model

    @property
    def role(self) -> str:
        return "DIVERSITY — catches Western-centric assumptions"

    async def generate(self, prompt: str, system: Optional[str] = None) -> ModelResponse:
        client = await self._get_client()
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        body = {"model": self._model, "messages": messages, "max_tokens": 4096}
        resp = await client.post(self.BASE_URL, headers=headers, json=body)
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        return ModelResponse(
            model=self._model,
            provider=self.name,
            content=content,
            raw=data,
            usage=data.get("usage"),
        )


class GoogleProvider(ModelProvider):
    """Gemini — search-grounded verification."""

    BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"

    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-2.0-flash"):
        super().__init__(api_key or os.getenv("GOOGLE_API_KEY"))
        self._model = model

    @property
    def name(self) -> str:
        return "gemini"

    @property
    def model_id(self) -> str:
        return self._model

    @property
    def role(self) -> str:
        return "GROUNDING — can verify against search"

    async def generate(self, prompt: str, system: Optional[str] = None) -> ModelResponse:
        client = await self._get_client()
        url = f"{self.BASE_URL}/{self._model}:generateContent?key={self.api_key}"

        parts = []
        if system:
            parts.append({"text": f"System: {system}\n\n{prompt}"})
        else:
            parts.append({"text": prompt})

        body = {"contents": [{"parts": parts}]}
        resp = await client.post(url, json=body)
        resp.raise_for_status()
        data = resp.json()
        content = data["candidates"][0]["content"]["parts"][0]["text"]
        return ModelResponse(
            model=self._model,
            provider=self.name,
            content=content,
            raw=data,
        )


def get_available_providers() -> list[ModelProvider]:
    """Return providers for which API keys are configured."""
    providers = []
    if os.getenv("ANTHROPIC_API_KEY"):
        providers.append(AnthropicProvider())
    if os.getenv("OPENAI_API_KEY"):
        providers.append(OpenAIProvider())
    if os.getenv("XAI_API_KEY"):
        providers.append(XAIProvider())
    if os.getenv("DEEPSEEK_API_KEY"):
        providers.append(DeepSeekProvider())
    if os.getenv("GOOGLE_API_KEY"):
        providers.append(GoogleProvider())
    return providers


def get_all_providers() -> dict[str, type[ModelProvider]]:
    """Return registry of all provider classes."""
    return {
        "claude": AnthropicProvider,
        "gpt": OpenAIProvider,
        "grok": XAIProvider,
        "deepseek": DeepSeekProvider,
        "gemini": GoogleProvider,
    }
