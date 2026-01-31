"""
Google Vertex AI LLM Provider.

Supports Gemini models via Google Cloud Vertex AI.
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


# Model mappings for Vertex AI
VERTEX_MODELS = {
    "gemini-pro": "gemini-1.0-pro",
    "gemini-pro-vision": "gemini-1.0-pro-vision",
    "gemini-1.5-pro": "gemini-1.5-pro-001",
    "gemini-1.5-flash": "gemini-1.5-flash-001",
    "gemini-2.0-flash": "gemini-2.0-flash-exp",
}


class VertexAIProvider(StreamingLLMProvider):
    """
    Google Vertex AI provider for Gemini models.

    Requires:
        pip install google-cloud-aiplatform

    Environment:
        GOOGLE_APPLICATION_CREDENTIALS: Path to service account JSON
        GOOGLE_CLOUD_PROJECT: GCP project ID (or pass in config)
    """

    provider = LLMProvider.VERTEX_AI
    capabilities = [
        ModelCapability.CHAT,
        ModelCapability.JSON_MODE,
        ModelCapability.STREAMING,
        ModelCapability.VISION,
    ]

    def __init__(self, config: LLMConfig):
        super().__init__(config)

        try:
            import vertexai
            from vertexai.generative_models import GenerativeModel
        except ImportError:
            raise ImportError(
                "google-cloud-aiplatform is required for Vertex AI. "
                "Install with: pip install google-cloud-aiplatform"
            )

        # Get project ID from config or environment
        project_id = config.project_id or os.getenv("GOOGLE_CLOUD_PROJECT")
        if not project_id:
            raise ValueError(
                "Google Cloud project ID is required. "
                "Set GOOGLE_CLOUD_PROJECT environment variable or pass project_id in config."
            )

        location = config.location or "us-central1"

        # Initialize Vertex AI
        vertexai.init(project=project_id, location=location)

        # Get model name (map common names to Vertex AI model IDs)
        model_name = VERTEX_MODELS.get(config.model, config.model)

        self._model = GenerativeModel(model_name)
        self._project_id = project_id
        self._location = location

    def _convert_messages(self, messages: list[Message]) -> tuple[Optional[str], list[dict]]:
        """Convert messages to Vertex AI format."""
        system_instruction = None
        contents = []

        for msg in messages:
            if msg.role == "system":
                system_instruction = msg.content
            elif msg.role == "user":
                contents.append({"role": "user", "parts": [{"text": msg.content}]})
            elif msg.role == "assistant":
                contents.append({"role": "model", "parts": [{"text": msg.content}]})

        return system_instruction, contents

    async def complete(
        self,
        messages: list[Message],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> LLMResponse:
        """Generate completion using Vertex AI."""
        from vertexai.generative_models import GenerationConfig

        system_instruction, contents = self._convert_messages(messages)

        generation_config = GenerationConfig(
            temperature=temperature or self.config.temperature,
            max_output_tokens=max_tokens or self.config.max_tokens,
            top_p=self.config.top_p,
        )

        # Create model with system instruction if provided
        if system_instruction:
            from vertexai.generative_models import GenerativeModel
            model = GenerativeModel(
                self._model._model_name,
                system_instruction=system_instruction,
            )
        else:
            model = self._model

        response = await model.generate_content_async(
            contents,
            generation_config=generation_config,
        )

        # Extract usage info
        usage = {}
        if hasattr(response, "usage_metadata"):
            usage = {
                "prompt_tokens": response.usage_metadata.prompt_token_count,
                "completion_tokens": response.usage_metadata.candidates_token_count,
                "total_tokens": response.usage_metadata.total_token_count,
            }

        result = LLMResponse(
            content=response.text,
            model=self.config.model,
            provider=self.provider,
            usage=usage,
            finish_reason=response.candidates[0].finish_reason.name if response.candidates else "stop",
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
        """Generate JSON completion using Vertex AI."""
        from vertexai.generative_models import GenerationConfig

        system_instruction, contents = self._convert_messages(messages)

        # Add JSON instruction to system prompt
        json_instruction = "\n\nYou must respond with valid JSON only. No other text or explanation."
        if system_instruction:
            system_instruction += json_instruction
        else:
            system_instruction = "You are a helpful assistant." + json_instruction

        generation_config = GenerationConfig(
            temperature=kwargs.get("temperature", self.config.temperature),
            max_output_tokens=self.config.max_tokens,
            response_mime_type="application/json",
        )

        from vertexai.generative_models import GenerativeModel
        model = GenerativeModel(
            self._model._model_name,
            system_instruction=system_instruction,
        )

        response = await model.generate_content_async(
            contents,
            generation_config=generation_config,
        )

        # Parse JSON response
        try:
            return json.loads(response.text)
        except json.JSONDecodeError:
            # Try to extract JSON from response
            text = response.text
            start = text.find("{")
            end = text.rfind("}") + 1
            if start != -1 and end > start:
                return json.loads(text[start:end])
            raise ValueError(f"Failed to parse JSON response: {text}")

    async def stream(
        self,
        messages: list[Message],
        **kwargs,
    ) -> AsyncIterator[str]:
        """Stream completion tokens."""
        from vertexai.generative_models import GenerationConfig

        system_instruction, contents = self._convert_messages(messages)

        generation_config = GenerationConfig(
            temperature=kwargs.get("temperature", self.config.temperature),
            max_output_tokens=self.config.max_tokens,
        )

        if system_instruction:
            from vertexai.generative_models import GenerativeModel
            model = GenerativeModel(
                self._model._model_name,
                system_instruction=system_instruction,
            )
        else:
            model = self._model

        response = await model.generate_content_async(
            contents,
            generation_config=generation_config,
            stream=True,
        )

        async for chunk in response:
            if chunk.text:
                yield chunk.text

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings using Vertex AI."""
        from vertexai.language_models import TextEmbeddingModel

        model = TextEmbeddingModel.from_pretrained("textembedding-gecko@003")
        embeddings = model.get_embeddings(texts)

        return [e.values for e in embeddings]
