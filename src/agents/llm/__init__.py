"""
LLM Provider integrations for agent intelligence.

Supports multiple providers:
- OpenAI (GPT-4, GPT-4o)
- Vertex AI (Gemini)
- Ollama (Llama, Mistral, CodeLlama, etc.)

Usage:
    from src.agents.llm import create_llm_provider, LLMConfig, LLMProvider

    # Auto-detect from environment
    provider = create_llm_provider()

    # Explicitly configure
    provider = create_llm_provider(LLMConfig(
        provider=LLMProvider.OLLAMA,
        model="llama3.1:70b"
    ))

    # Use the provider
    response = await provider.complete_simple(
        "You are a helpful assistant.",
        "What is 2+2?"
    )
"""

# Base types
from .base import (
    BaseLLMProvider,
    StreamingLLMProvider,
    LLMConfig,
    LLMProvider,
    LLMResponse,
    Message,
    ModelCapability,
)

# Factory
from .factory import (
    create_llm_provider,
    get_available_providers,
    list_models,
    LLMClient,
)

# Providers
from .openai_provider import OpenAIProvider
from .vertex_provider import VertexAIProvider
from .ollama_provider import OllamaProvider

# Prompts
from .prompts import AgentPrompts

# Backward compatibility
from .openai_client import OpenAIClient, LLMConfig as LegacyLLMConfig

__all__ = [
    # Base
    "BaseLLMProvider",
    "StreamingLLMProvider",
    "LLMConfig",
    "LLMProvider",
    "LLMResponse",
    "Message",
    "ModelCapability",
    # Factory
    "create_llm_provider",
    "get_available_providers",
    "list_models",
    "LLMClient",
    # Providers
    "OpenAIProvider",
    "VertexAIProvider",
    "OllamaProvider",
    # Prompts
    "AgentPrompts",
    # Backward compatibility
    "OpenAIClient",
]
