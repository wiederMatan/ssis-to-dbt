"""
Ollama LLM Provider for local models.

Supports Llama, Mistral, CodeLlama, and other models via Ollama.
"""

import json
import aiohttp
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


# Common Ollama model names
OLLAMA_MODELS = {
    # Llama models
    "llama3": "llama3",
    "llama3:8b": "llama3:8b",
    "llama3:70b": "llama3:70b",
    "llama3.1": "llama3.1",
    "llama3.1:8b": "llama3.1:8b",
    "llama3.1:70b": "llama3.1:70b",
    "llama3.2": "llama3.2",
    "llama3.3": "llama3.3",
    "llama3.3:70b": "llama3.3:70b",
    # Code models
    "codellama": "codellama",
    "codellama:34b": "codellama:34b",
    "deepseek-coder": "deepseek-coder",
    "deepseek-coder-v2": "deepseek-coder-v2",
    # Mistral
    "mistral": "mistral",
    "mixtral": "mixtral",
    "mixtral:8x7b": "mixtral:8x7b",
    # Other
    "phi3": "phi3",
    "gemma2": "gemma2",
    "qwen2.5": "qwen2.5",
    "qwen2.5-coder": "qwen2.5-coder",
}


class OllamaProvider(StreamingLLMProvider):
    """
    Ollama provider for local LLM inference.

    Supports Llama, Mistral, CodeLlama, and many other models.

    Requirements:
        1. Install Ollama: https://ollama.ai
        2. Pull a model: ollama pull llama3.1
        3. Start server: ollama serve

    Environment:
        OLLAMA_HOST: Ollama server URL (default: http://localhost:11434)
    """

    provider = LLMProvider.OLLAMA
    capabilities = [
        ModelCapability.CHAT,
        ModelCapability.JSON_MODE,
        ModelCapability.STREAMING,
    ]

    def __init__(self, config: LLMConfig):
        super().__init__(config)

        import os
        self._host = config.ollama_host or os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self._model = OLLAMA_MODELS.get(config.model, config.model)

    def _convert_messages(self, messages: list[Message]) -> list[dict]:
        """Convert messages to Ollama format."""
        result = []
        for msg in messages:
            result.append({
                "role": msg.role,
                "content": msg.content,
            })
        return result

    async def _request(
        self,
        endpoint: str,
        data: dict,
        stream: bool = False,
    ) -> aiohttp.ClientResponse:
        """Make request to Ollama API."""
        url = f"{self._host}{endpoint}"

        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                json=data,
                timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds),
            ) as response:
                if response.status != 200:
                    text = await response.text()
                    raise RuntimeError(f"Ollama request failed: {text}")

                if stream:
                    return response
                else:
                    return await response.json()

    async def complete(
        self,
        messages: list[Message],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> LLMResponse:
        """Generate completion using Ollama."""
        ollama_messages = self._convert_messages(messages)

        data = {
            "model": self._model,
            "messages": ollama_messages,
            "stream": False,
            "options": {
                "temperature": temperature or self.config.temperature,
                "num_predict": max_tokens or self.config.max_tokens,
                "top_p": self.config.top_p,
            },
        }

        url = f"{self._host}/api/chat"

        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                json=data,
                timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds),
            ) as response:
                if response.status != 200:
                    text = await response.text()
                    raise RuntimeError(f"Ollama request failed: {text}")

                result = await response.json()

        # Extract content and usage
        content = result.get("message", {}).get("content", "")

        usage = {
            "prompt_tokens": result.get("prompt_eval_count", 0),
            "completion_tokens": result.get("eval_count", 0),
        }
        usage["total_tokens"] = usage["prompt_tokens"] + usage["completion_tokens"]

        llm_response = LLMResponse(
            content=content,
            model=self._model,
            provider=self.provider,
            usage=usage,
            finish_reason="stop" if result.get("done") else "length",
            raw_response=result,
        )

        self._update_stats(llm_response)
        return llm_response

    async def complete_json(
        self,
        messages: list[Message],
        schema: Optional[dict] = None,
        **kwargs,
    ) -> dict[str, Any]:
        """Generate JSON completion using Ollama."""
        # Add JSON format instruction
        json_instruction = "\n\nRespond with valid JSON only. No other text, markdown, or explanation."

        modified_messages = []
        for msg in messages:
            if msg.role == "system":
                modified_messages.append(Message(
                    role="system",
                    content=msg.content + json_instruction,
                ))
            else:
                modified_messages.append(msg)

        # If no system message, add one
        if not any(m.role == "system" for m in modified_messages):
            modified_messages.insert(0, Message(
                role="system",
                content="You are a helpful assistant. " + json_instruction,
            ))

        ollama_messages = self._convert_messages(modified_messages)

        data = {
            "model": self._model,
            "messages": ollama_messages,
            "stream": False,
            "format": "json",  # Ollama's JSON mode
            "options": {
                "temperature": kwargs.get("temperature", self.config.temperature),
                "num_predict": self.config.max_tokens,
            },
        }

        url = f"{self._host}/api/chat"

        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                json=data,
                timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds),
            ) as response:
                if response.status != 200:
                    text = await response.text()
                    raise RuntimeError(f"Ollama request failed: {text}")

                result = await response.json()

        content = result.get("message", {}).get("content", "")

        # Parse JSON
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # Try to extract JSON from response
            start = content.find("{")
            end = content.rfind("}") + 1
            if start != -1 and end > start:
                return json.loads(content[start:end])

            # Try array
            start = content.find("[")
            end = content.rfind("]") + 1
            if start != -1 and end > start:
                return json.loads(content[start:end])

            raise ValueError(f"Failed to parse JSON response: {content}")

    async def stream(
        self,
        messages: list[Message],
        **kwargs,
    ) -> AsyncIterator[str]:
        """Stream completion tokens from Ollama."""
        ollama_messages = self._convert_messages(messages)

        data = {
            "model": self._model,
            "messages": ollama_messages,
            "stream": True,
            "options": {
                "temperature": kwargs.get("temperature", self.config.temperature),
                "num_predict": self.config.max_tokens,
            },
        }

        url = f"{self._host}/api/chat"

        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                json=data,
                timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds),
            ) as response:
                if response.status != 200:
                    text = await response.text()
                    raise RuntimeError(f"Ollama request failed: {text}")

                async for line in response.content:
                    if line:
                        try:
                            chunk = json.loads(line.decode("utf-8"))
                            content = chunk.get("message", {}).get("content", "")
                            if content:
                                yield content

                            if chunk.get("done"):
                                break
                        except json.JSONDecodeError:
                            continue

    async def list_models(self) -> list[dict]:
        """List available models in Ollama."""
        url = f"{self._host}/api/tags"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    text = await response.text()
                    raise RuntimeError(f"Failed to list models: {text}")

                result = await response.json()
                return result.get("models", [])

    async def pull_model(self, model_name: str) -> None:
        """Pull a model from Ollama registry."""
        url = f"{self._host}/api/pull"

        data = {"name": model_name, "stream": False}

        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                json=data,
                timeout=aiohttp.ClientTimeout(total=600),  # 10 min for large models
            ) as response:
                if response.status != 200:
                    text = await response.text()
                    raise RuntimeError(f"Failed to pull model: {text}")

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings using Ollama."""
        url = f"{self._host}/api/embeddings"
        embeddings = []

        async with aiohttp.ClientSession() as session:
            for text in texts:
                data = {
                    "model": self._model,
                    "prompt": text,
                }

                async with session.post(url, json=data) as response:
                    if response.status != 200:
                        text = await response.text()
                        raise RuntimeError(f"Embedding request failed: {text}")

                    result = await response.json()
                    embeddings.append(result.get("embedding", []))

        return embeddings

    async def health_check(self) -> bool:
        """Check if Ollama server is running."""
        try:
            url = f"{self._host}/api/tags"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    return response.status == 200
        except Exception:
            return False
