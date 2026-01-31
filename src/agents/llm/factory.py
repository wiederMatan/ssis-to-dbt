"""
LLM Provider Factory.

Creates the appropriate LLM provider based on configuration.
"""

import os
from typing import Optional

from .base import BaseLLMProvider, LLMConfig, LLMProvider


def create_llm_provider(config: Optional[LLMConfig] = None) -> BaseLLMProvider:
    """
    Create an LLM provider based on configuration.

    Args:
        config: LLM configuration. If None, will auto-detect from environment.

    Returns:
        Configured LLM provider instance

    Environment Variables (for auto-detection):
        OPENAI_API_KEY: Use OpenAI
        GOOGLE_APPLICATION_CREDENTIALS: Use Vertex AI
        OLLAMA_HOST or OLLAMA_MODEL: Use Ollama

    Example:
        # Auto-detect provider from environment
        provider = create_llm_provider()

        # Explicitly use OpenAI
        provider = create_llm_provider(LLMConfig(
            provider=LLMProvider.OPENAI,
            model="gpt-4o"
        ))

        # Use Vertex AI with Gemini
        provider = create_llm_provider(LLMConfig(
            provider=LLMProvider.VERTEX_AI,
            model="gemini-1.5-pro",
            project_id="my-project"
        ))

        # Use local Llama via Ollama
        provider = create_llm_provider(LLMConfig(
            provider=LLMProvider.OLLAMA,
            model="llama3.1:70b",
            ollama_host="http://localhost:11434"
        ))
    """
    if config is None:
        config = _auto_detect_config()

    provider_type = config.provider

    if provider_type == LLMProvider.OPENAI:
        from .openai_provider import OpenAIProvider
        return OpenAIProvider(config)

    elif provider_type == LLMProvider.VERTEX_AI:
        from .vertex_provider import VertexAIProvider
        return VertexAIProvider(config)

    elif provider_type == LLMProvider.OLLAMA:
        from .ollama_provider import OllamaProvider
        return OllamaProvider(config)

    elif provider_type == LLMProvider.ANTHROPIC:
        raise NotImplementedError("Anthropic provider not yet implemented")

    elif provider_type == LLMProvider.AZURE_OPENAI:
        raise NotImplementedError("Azure OpenAI provider not yet implemented")

    else:
        raise ValueError(f"Unknown provider: {provider_type}")


def _auto_detect_config() -> LLMConfig:
    """
    Auto-detect LLM configuration from environment variables.

    Priority:
    1. OPENAI_API_KEY -> OpenAI
    2. GOOGLE_APPLICATION_CREDENTIALS -> Vertex AI
    3. OLLAMA_HOST or OLLAMA_MODEL -> Ollama
    4. Default to OpenAI (will fail if no API key)
    """
    # Check for OpenAI
    if os.getenv("OPENAI_API_KEY"):
        return LLMConfig(
            provider=LLMProvider.OPENAI,
            model=os.getenv("OPENAI_MODEL", "gpt-4o"),
        )

    # Check for Vertex AI
    if os.getenv("GOOGLE_APPLICATION_CREDENTIALS") or os.getenv("GOOGLE_CLOUD_PROJECT"):
        return LLMConfig(
            provider=LLMProvider.VERTEX_AI,
            model=os.getenv("VERTEX_MODEL", "gemini-1.5-pro"),
            project_id=os.getenv("GOOGLE_CLOUD_PROJECT"),
            location=os.getenv("VERTEX_LOCATION", "us-central1"),
        )

    # Check for Ollama
    if os.getenv("OLLAMA_HOST") or os.getenv("OLLAMA_MODEL"):
        return LLMConfig(
            provider=LLMProvider.OLLAMA,
            model=os.getenv("OLLAMA_MODEL", "llama3.1"),
            ollama_host=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
        )

    # Default to OpenAI (will require API key to be set)
    return LLMConfig(provider=LLMProvider.OPENAI, model="gpt-4o")


def get_available_providers() -> dict[str, bool]:
    """
    Check which LLM providers are available based on environment.

    Returns:
        Dict mapping provider name to availability status
    """
    available = {}

    # OpenAI
    available["openai"] = bool(os.getenv("OPENAI_API_KEY"))

    # Vertex AI
    available["vertex_ai"] = bool(
        os.getenv("GOOGLE_APPLICATION_CREDENTIALS") or
        os.getenv("GOOGLE_CLOUD_PROJECT")
    )

    # Ollama - check if server is running
    import asyncio
    async def check_ollama():
        try:
            from .ollama_provider import OllamaProvider
            provider = OllamaProvider(LLMConfig(
                provider=LLMProvider.OLLAMA,
                model="llama3.1",
            ))
            return await provider.health_check()
        except Exception:
            return False

    try:
        available["ollama"] = asyncio.get_event_loop().run_until_complete(check_ollama())
    except Exception:
        available["ollama"] = False

    return available


def list_models(provider: LLMProvider) -> list[str]:
    """
    List recommended models for a provider.

    Args:
        provider: The LLM provider

    Returns:
        List of recommended model names
    """
    models = {
        LLMProvider.OPENAI: [
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4-turbo",
            "gpt-4",
            "gpt-3.5-turbo",
        ],
        LLMProvider.VERTEX_AI: [
            "gemini-2.0-flash",
            "gemini-1.5-pro",
            "gemini-1.5-flash",
            "gemini-pro",
        ],
        LLMProvider.OLLAMA: [
            "llama3.3:70b",
            "llama3.1:70b",
            "llama3.1:8b",
            "llama3.1",
            "codellama:34b",
            "deepseek-coder-v2",
            "mixtral:8x7b",
            "mistral",
            "qwen2.5-coder",
        ],
    }

    return models.get(provider, [])


# Convenience class for backward compatibility
class LLMClient:
    """
    Unified LLM client that wraps any provider.

    Provides the same interface as the old OpenAIClient for backward compatibility.
    """

    def __init__(self, config: Optional[LLMConfig] = None):
        self._provider = create_llm_provider(config)
        self.config = self._provider.config

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Get a completion."""
        return await self._provider.complete_simple(
            system_prompt,
            user_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    async def complete_with_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
    ) -> dict:
        """Get a JSON completion."""
        return await self._provider.complete_json_simple(
            system_prompt,
            user_prompt,
            temperature=temperature,
        )

    async def analyze_sql(self, sql: str) -> dict:
        """Analyze SQL statement."""
        from .prompts import AgentPrompts

        return await self.complete_with_json(
            AgentPrompts.SQL_ANALYZER,
            f"Analyze this SQL statement:\n\n```sql\n{sql}\n```",
        )

    async def detect_load_pattern(self, package_summary: dict) -> dict:
        """Detect load pattern from package analysis."""
        import json
        from .prompts import AgentPrompts

        return await self.complete_with_json(
            AgentPrompts.PATTERN_DETECTOR,
            f"Analyze this SSIS package summary:\n\n```json\n{json.dumps(package_summary, indent=2)}\n```",
        )

    async def generate_dbt_model(self, task_info: dict, layer: str) -> dict:
        """Generate dbt model from SSIS task info."""
        import json
        from .prompts import AgentPrompts

        system_prompt = (
            AgentPrompts.DBT_STAGING_GENERATOR
            if layer == "staging"
            else AgentPrompts.DBT_CORE_GENERATOR
        )

        return await self.complete_with_json(
            system_prompt,
            f"Generate dbt {layer} model from this SSIS task:\n\n```json\n{json.dumps(task_info, indent=2)}\n```",
        )

    async def diagnose_validation_failure(
        self,
        validation_result: dict,
        model_info: dict,
    ) -> dict:
        """Diagnose validation failure."""
        import json
        from .prompts import AgentPrompts

        return await self.complete_with_json(
            AgentPrompts.FAILURE_DIAGNOSER,
            f"""Diagnose this validation failure:

Validation Result:
```json
{json.dumps(validation_result, indent=2)}
```

Model Info:
```json
{json.dumps(model_info, indent=2)}
```""",
        )

    @property
    def provider(self) -> BaseLLMProvider:
        """Get the underlying provider."""
        return self._provider

    def get_stats(self) -> dict:
        """Get usage statistics."""
        return self._provider.get_stats()
