"""
Base LLM Provider interface and common types.

Defines the contract that all LLM providers must implement.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional, AsyncIterator
from pydantic import BaseModel, Field


class LLMProvider(str, Enum):
    """Supported LLM providers."""

    OPENAI = "openai"
    VERTEX_AI = "vertex_ai"
    OLLAMA = "ollama"  # For Llama and other local models
    ANTHROPIC = "anthropic"
    AZURE_OPENAI = "azure_openai"


class ModelCapability(str, Enum):
    """Capabilities that models may support."""

    CHAT = "chat"
    JSON_MODE = "json_mode"
    FUNCTION_CALLING = "function_calling"
    VISION = "vision"
    STREAMING = "streaming"
    EMBEDDINGS = "embeddings"


@dataclass
class Message:
    """A chat message."""

    role: str  # "system", "user", "assistant", "tool"
    content: str
    name: Optional[str] = None
    tool_call_id: Optional[str] = None
    tool_calls: Optional[list[dict]] = None


@dataclass
class LLMResponse:
    """Response from LLM completion."""

    content: str
    model: str
    provider: LLMProvider
    usage: dict[str, int] = field(default_factory=dict)
    finish_reason: str = "stop"
    tool_calls: Optional[list[dict]] = None
    raw_response: Optional[Any] = None

    @property
    def input_tokens(self) -> int:
        return self.usage.get("prompt_tokens", 0)

    @property
    def output_tokens(self) -> int:
        return self.usage.get("completion_tokens", 0)

    @property
    def total_tokens(self) -> int:
        return self.usage.get("total_tokens", self.input_tokens + self.output_tokens)


class LLMConfig(BaseModel):
    """Base configuration for LLM providers."""

    provider: LLMProvider = LLMProvider.OPENAI
    model: str = "gpt-4o"
    temperature: float = 0.2
    max_tokens: int = 4096
    top_p: float = 1.0
    timeout_seconds: float = 60.0
    max_retries: int = 3

    # Provider-specific settings
    api_key: Optional[str] = None
    api_base: Optional[str] = None

    # Vertex AI specific
    project_id: Optional[str] = None
    location: Optional[str] = "us-central1"

    # Ollama specific
    ollama_host: str = "http://localhost:11434"

    class Config:
        use_enum_values = True


class BaseLLMProvider(ABC):
    """
    Abstract base class for LLM providers.

    All providers must implement these methods to ensure
    consistent behavior across different LLM backends.
    """

    provider: LLMProvider
    capabilities: list[ModelCapability]

    def __init__(self, config: LLMConfig):
        self.config = config
        self._request_count = 0
        self._total_tokens = 0

    @abstractmethod
    async def complete(
        self,
        messages: list[Message],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> LLMResponse:
        """
        Generate a completion from the LLM.

        Args:
            messages: List of chat messages
            temperature: Override config temperature
            max_tokens: Override config max tokens
            **kwargs: Provider-specific options

        Returns:
            LLMResponse with generated content
        """
        pass

    @abstractmethod
    async def complete_json(
        self,
        messages: list[Message],
        schema: Optional[dict] = None,
        **kwargs,
    ) -> dict[str, Any]:
        """
        Generate a JSON completion.

        Args:
            messages: List of chat messages
            schema: Optional JSON schema for validation
            **kwargs: Provider-specific options

        Returns:
            Parsed JSON response
        """
        pass

    async def complete_simple(
        self,
        system_prompt: str,
        user_prompt: str,
        **kwargs,
    ) -> str:
        """
        Simplified completion with system and user prompts.

        Args:
            system_prompt: System message
            user_prompt: User message
            **kwargs: Additional options

        Returns:
            Generated text content
        """
        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=user_prompt),
        ]
        response = await self.complete(messages, **kwargs)
        return response.content

    async def complete_json_simple(
        self,
        system_prompt: str,
        user_prompt: str,
        **kwargs,
    ) -> dict[str, Any]:
        """
        Simplified JSON completion.

        Args:
            system_prompt: System message (should instruct JSON output)
            user_prompt: User message
            **kwargs: Additional options

        Returns:
            Parsed JSON response
        """
        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=user_prompt),
        ]
        return await self.complete_json(messages, **kwargs)

    def supports(self, capability: ModelCapability) -> bool:
        """Check if provider supports a capability."""
        return capability in self.capabilities

    def get_stats(self) -> dict[str, Any]:
        """Get usage statistics."""
        return {
            "provider": self.provider.value,
            "model": self.config.model,
            "request_count": self._request_count,
            "total_tokens": self._total_tokens,
        }

    def _update_stats(self, response: LLMResponse) -> None:
        """Update internal statistics."""
        self._request_count += 1
        self._total_tokens += response.total_tokens


class StreamingLLMProvider(BaseLLMProvider):
    """Extended base class for providers that support streaming."""

    @abstractmethod
    async def stream(
        self,
        messages: list[Message],
        **kwargs,
    ) -> AsyncIterator[str]:
        """
        Stream completion tokens.

        Args:
            messages: List of chat messages
            **kwargs: Provider-specific options

        Yields:
            Generated tokens as they arrive
        """
        pass
