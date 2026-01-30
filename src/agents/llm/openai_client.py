"""OpenAI API client wrapper for agent LLM calls."""

import os
from typing import Any, Optional
from pydantic import BaseModel

try:
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = None  # type: ignore


class LLMConfig(BaseModel):
    """Configuration for LLM client."""

    model: str = "gpt-4o"
    temperature: float = 0.2
    max_tokens: int = 4096
    api_key: Optional[str] = None


class OpenAIClient:
    """Async OpenAI client for agent LLM calls."""

    def __init__(self, config: Optional[LLMConfig] = None):
        if AsyncOpenAI is None:
            raise ImportError(
                "openai package is required. Install with: pip install openai"
            )

        self.config = config or LLMConfig()
        api_key = self.config.api_key or os.getenv("OPENAI_API_KEY")

        if not api_key:
            raise ValueError(
                "OpenAI API key is required. Set OPENAI_API_KEY environment variable "
                "or pass api_key in config."
            )

        self.client = AsyncOpenAI(api_key=api_key)

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Get a completion from OpenAI.

        Args:
            system_prompt: System message defining the assistant's role
            user_prompt: User message with the task/question
            temperature: Override default temperature
            max_tokens: Override default max tokens

        Returns:
            The assistant's response text
        """
        response = await self.client.chat.completions.create(
            model=self.config.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature or self.config.temperature,
            max_tokens=max_tokens or self.config.max_tokens,
        )

        return response.choices[0].message.content or ""

    async def complete_with_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
    ) -> dict[str, Any]:
        """
        Get a JSON completion from OpenAI.

        Args:
            system_prompt: System message (should instruct JSON output)
            user_prompt: User message with the task/question

        Returns:
            Parsed JSON response
        """
        import json

        response = await self.client.chat.completions.create(
            model=self.config.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature or self.config.temperature,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content or "{}"
        return json.loads(content)

    async def analyze_sql(self, sql: str) -> dict[str, Any]:
        """
        Analyze SQL statement to understand its purpose and components.

        Args:
            sql: SQL statement to analyze

        Returns:
            Analysis including tables, columns, joins, filters, etc.
        """
        from .prompts import AgentPrompts

        system_prompt = AgentPrompts.SQL_ANALYZER
        user_prompt = f"Analyze this SQL statement:\n\n```sql\n{sql}\n```"

        return await self.complete_with_json(system_prompt, user_prompt)

    async def detect_load_pattern(
        self,
        package_summary: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Detect load pattern (incremental vs full) from package analysis.

        Args:
            package_summary: Summary of SSIS package components

        Returns:
            Load pattern detection with confidence and indicators
        """
        import json
        from .prompts import AgentPrompts

        system_prompt = AgentPrompts.PATTERN_DETECTOR
        user_prompt = f"Analyze this SSIS package summary:\n\n```json\n{json.dumps(package_summary, indent=2)}\n```"

        return await self.complete_with_json(system_prompt, user_prompt)

    async def generate_dbt_model(
        self,
        task_info: dict[str, Any],
        layer: str,
    ) -> dict[str, Any]:
        """
        Generate dbt model SQL and YAML from SSIS task info.

        Args:
            task_info: Information about the SSIS task
            layer: Target layer ("staging" or "core")

        Returns:
            Generated SQL and YAML content
        """
        import json
        from .prompts import AgentPrompts

        system_prompt = (
            AgentPrompts.DBT_STAGING_GENERATOR
            if layer == "staging"
            else AgentPrompts.DBT_CORE_GENERATOR
        )
        user_prompt = f"Generate dbt {layer} model from this SSIS task:\n\n```json\n{json.dumps(task_info, indent=2)}\n```"

        return await self.complete_with_json(system_prompt, user_prompt)

    async def diagnose_validation_failure(
        self,
        validation_result: dict[str, Any],
        model_info: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Diagnose why validation failed and suggest fixes.

        Args:
            validation_result: The failed validation result
            model_info: Information about the dbt model

        Returns:
            Diagnosis with root cause and suggested fixes
        """
        import json
        from .prompts import AgentPrompts

        system_prompt = AgentPrompts.FAILURE_DIAGNOSER
        user_prompt = f"""Diagnose this validation failure:

Validation Result:
```json
{json.dumps(validation_result, indent=2)}
```

Model Info:
```json
{json.dumps(model_info, indent=2)}
```"""

        return await self.complete_with_json(system_prompt, user_prompt)
