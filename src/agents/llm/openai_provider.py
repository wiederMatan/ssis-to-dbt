"""
OpenAI LLM Provider.

Supports GPT-4, GPT-4o, GPT-3.5, and other OpenAI models.
"""

import json
import os
from typing import Any, Optional, AsyncIterator

from .base import (
    BaseLLMProvider,
    StreamingLLMProvider,
    LLMConfig,
    LLMProvider,
    LLMResponse,
    Message,
    ModelCapability,
)


class OpenAIProvider(StreamingLLMProvider):
    """
    OpenAI API provider.

    Supports GPT-4, GPT-4o, GPT-3.5 Turbo, and other models.

    Requirements:
        pip install openai

    Environment:
        OPENAI_API_KEY: Your OpenAI API key
    """

    provider = LLMProvider.OPENAI
    capabilities = [
        ModelCapability.CHAT,
        ModelCapability.JSON_MODE,
        ModelCapability.FUNCTION_CALLING,
        ModelCapability.STREAMING,
        ModelCapability.VISION,
        ModelCapability.EMBEDDINGS,
    ]

    def __init__(self, config: LLMConfig):
        super().__init__(config)

        try:
            from openai import AsyncOpenAI
        except ImportError:
            raise ImportError(
                "openai package is required. Install with: pip install openai"
            )

        api_key = config.api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OpenAI API key is required. "
                "Set OPENAI_API_KEY environment variable or pass api_key in config."
            )

        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url=config.api_base,
            timeout=config.timeout_seconds,
            max_retries=config.max_retries,
        )

    def _convert_messages(self, messages: list[Message]) -> list[dict]:
        """Convert messages to OpenAI format."""
        result = []
        for msg in messages:
            m = {"role": msg.role, "content": msg.content}
            if msg.name:
                m["name"] = msg.name
            if msg.tool_call_id:
                m["tool_call_id"] = msg.tool_call_id
            if msg.tool_calls:
                m["tool_calls"] = msg.tool_calls
            result.append(m)
        return result

    async def complete(
        self,
        messages: list[Message],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> LLMResponse:
        """Generate completion using OpenAI."""
        openai_messages = self._convert_messages(messages)

        response = await self._client.chat.completions.create(
            model=self.config.model,
            messages=openai_messages,
            temperature=temperature or self.config.temperature,
            max_tokens=max_tokens or self.config.max_tokens,
            top_p=self.config.top_p,
            **kwargs,
        )

        # Extract usage
        usage = {}
        if response.usage:
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }

        # Extract tool calls if any
        tool_calls = None
        if response.choices[0].message.tool_calls:
            tool_calls = [
                {
                    "id": tc.id,
                    "type": tc.type,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in response.choices[0].message.tool_calls
            ]

        result = LLMResponse(
            content=response.choices[0].message.content or "",
            model=response.model,
            provider=self.provider,
            usage=usage,
            finish_reason=response.choices[0].finish_reason or "stop",
            tool_calls=tool_calls,
            raw_response=response,
        )

        self._update_stats(result)
        return result

    async def complete_json(
        self,
        messages: list[Message],
        schema: Optional[dict] = None,
        **kwargs,
    ) -> dict[str, Any]:
        """Generate JSON completion using OpenAI."""
        openai_messages = self._convert_messages(messages)

        response = await self._client.chat.completions.create(
            model=self.config.model,
            messages=openai_messages,
            temperature=kwargs.get("temperature", self.config.temperature),
            response_format={"type": "json_object"},
            **kwargs,
        )

        content = response.choices[0].message.content or "{}"

        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # Try to extract JSON
            start = content.find("{")
            end = content.rfind("}") + 1
            if start != -1 and end > start:
                return json.loads(content[start:end])
            raise ValueError(f"Failed to parse JSON response: {content}")

    async def stream(
        self,
        messages: list[Message],
        **kwargs,
    ) -> AsyncIterator[str]:
        """Stream completion tokens from OpenAI."""
        openai_messages = self._convert_messages(messages)

        response = await self._client.chat.completions.create(
            model=self.config.model,
            messages=openai_messages,
            temperature=kwargs.get("temperature", self.config.temperature),
            max_tokens=self.config.max_tokens,
            stream=True,
            **kwargs,
        )

        async for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    async def complete_with_tools(
        self,
        messages: list[Message],
        tools: list[dict],
        tool_choice: str = "auto",
        **kwargs,
    ) -> LLMResponse:
        """Generate completion with function calling."""
        openai_messages = self._convert_messages(messages)

        response = await self._client.chat.completions.create(
            model=self.config.model,
            messages=openai_messages,
            temperature=kwargs.get("temperature", self.config.temperature),
            tools=tools,
            tool_choice=tool_choice,
            **kwargs,
        )

        usage = {}
        if response.usage:
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }

        tool_calls = None
        if response.choices[0].message.tool_calls:
            tool_calls = [
                {
                    "id": tc.id,
                    "type": tc.type,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in response.choices[0].message.tool_calls
            ]

        result = LLMResponse(
            content=response.choices[0].message.content or "",
            model=response.model,
            provider=self.provider,
            usage=usage,
            finish_reason=response.choices[0].finish_reason or "stop",
            tool_calls=tool_calls,
            raw_response=response,
        )

        self._update_stats(result)
        return result

    async def embed(self, texts: list[str], model: str = "text-embedding-3-small") -> list[list[float]]:
        """Generate embeddings using OpenAI."""
        response = await self._client.embeddings.create(
            model=model,
            input=texts,
        )

        return [e.embedding for e in response.data]
