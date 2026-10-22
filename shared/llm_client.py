"""
🤖 Unified LLM Client
Supports OpenAI & Anthropic with automatic model routing.
"""

import json
import os
from typing import Optional


class LLMClient:
    """
    Unified LLM interface — wraps OpenAI and Anthropic APIs.
    Supports model arbitrage: use cheap models for routing, expensive ones for reasoning.
    """

    def __init__(self, provider: str = "openai", model: str = "gpt-4o-mini",
                 max_tokens: int = 4000):
        self.provider = provider
        self.model = model
        self.max_tokens = max_tokens
        self._client = None
        self._total_tokens = 0

    def _get_openai_client(self):
        if self._client is None:
            try:
                from openai import AsyncOpenAI
                self._client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            except ImportError:
                raise ImportError("pip install openai")
        return self._client

    def _get_anthropic_client(self):
        if self._client is None:
            try:
                from anthropic import AsyncAnthropic
                self._client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
            except ImportError:
                raise ImportError("pip install anthropic")
        return self._client

    async def chat(self, system: str, user: str,
                   temperature: float = 0.7,
                   response_format: Optional[str] = None) -> str:
        """
        Send a chat message and get a response.
        Returns the raw text response.
        """
        if self.provider == "openai":
            return await self._chat_openai(system, user, temperature, response_format)
        elif self.provider == "anthropic":
            return await self._chat_anthropic(system, user, temperature)
        else:
            raise ValueError(f"Unknown provider: {self.provider}")

    async def _chat_openai(self, system: str, user: str,
                           temperature: float, response_format: Optional[str]) -> str:
        client = self._get_openai_client()
        kwargs = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
            "max_tokens": self.max_tokens,
        }
        if response_format == "json":
            kwargs["response_format"] = {"type": "json_object"}

        response = await client.chat.completions.create(**kwargs)
        self._total_tokens += response.usage.total_tokens if response.usage else 0
        return response.choices[0].message.content or ""

    async def _chat_anthropic(self, system: str, user: str,
                              temperature: float) -> str:
        client = self._get_anthropic_client()
        response = await client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
            temperature=temperature,
        )
        usage = response.usage
        self._total_tokens += (usage.input_tokens + usage.output_tokens) if usage else 0
        return response.content[0].text if response.content else ""

    async def chat_json(self, system: str, user: str, temperature: float = 0.3) -> dict:
        """Chat and parse response as JSON"""
        if self.provider == "openai":
            text = await self._chat_openai(system, user, temperature, response_format="json")
        else:
            # For Anthropic, add JSON instruction
            user_with_json = user + "\n\nRespond with valid JSON only. No markdown formatting."
            text = await self._chat_anthropic(system, user_with_json, temperature)

        # Clean and parse
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1])

        return json.loads(text)

    @property
    def total_tokens_used(self) -> int:
        return self._total_tokens
