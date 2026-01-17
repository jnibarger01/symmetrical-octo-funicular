"""Codex Executor - LLM interaction and code generation."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from openai import AsyncOpenAI, OpenAIError

from ..core.config import Config
from ..core.models import LLMRequest, LLMResponse, Task

logger = logging.getLogger(__name__)


class CodexExecutorError(Exception):
    """Base exception for Codex executor errors."""

    pass


class CodexExecutor:
    """
    Codex executor for LLM-powered code generation.

    Handles prompt construction, LLM API calls, response parsing,
    and caching.
    """

    def __init__(self, config: Config) -> None:
        """
        Initialize the Codex executor.

        Args:
            config: Configuration object
        """
        self.config = config
        self.client = AsyncOpenAI(api_key=config.llm.api_key)
        self.cache_dir = config.cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    async def execute_task(
        self, task: Task, context: dict[str, Any]
    ) -> tuple[str, LLMRequest, LLMResponse]:
        """
        Execute a task using the LLM.

        Args:
            task: Task to execute
            context: Execution context (file contents, related code, etc.)

        Returns:
            Tuple of (generated_code, request, response)

        Raises:
            CodexExecutorError: If execution fails
        """
        # Build prompt
        prompt = self._build_prompt(task, context)

        # Check cache
        cache_key = self._get_cache_key(prompt, self.config.llm.model)
        cached_response = self._get_from_cache(cache_key)

        if cached_response:
            logger.info(f"Cache hit for task {task.id}")
            # Build a dummy request for the cached response
            request = LLMRequest(
                task_id=task.id,
                model=self.config.llm.model,
                temperature=self.config.llm.temperature,
                max_tokens=self.config.llm.max_tokens_per_request,
            )
            return cached_response, request, LLMResponse(
                request_id=request.id, content=cached_response, finish_reason="cached", cached=True
            )

        # Make LLM call
        request, response = await self._call_llm(task, prompt)

        # Cache the response
        self._save_to_cache(cache_key, response.content)

        return response.content, request, response

    def _build_prompt(self, task: Task, context: dict[str, Any]) -> str:
        """
        Build the prompt for the LLM.

        Args:
            task: Task to execute
            context: Execution context

        Returns:
            Formatted prompt
        """
        # System prompt
        system_prompt = """You are an expert software engineer working on a coding task.
Your goal is to write clean, efficient, and well-tested code that follows best practices.

Guidelines:
- Write clear, readable code with appropriate comments
- Follow the project's existing code style and conventions
- Include error handling where appropriate
- Consider edge cases and potential issues
- Write code that is maintainable and extensible
"""

        # Task specification
        task_spec = f"""
## Task: {task.title}

{task.description}

Task Type: {task.type}
Priority: {task.priority}
Complexity: {task.estimated_complexity}/5
"""

        # Target files context
        files_context = ""
        if task.target_files:
            files_context = "\n## Target Files\n"
            for file_path in task.target_files:
                file_content = context.get("files", {}).get(file_path, "")
                if file_content:
                    files_context += f"\n### {file_path}\n```\n{file_content}\n```\n"

        # Related code context
        related_context = ""
        related_files = context.get("related_files", {})
        if related_files:
            related_context = "\n## Related Code\n"
            for file_path, summary in related_files.items():
                related_context += f"\n### {file_path}\n{summary}\n"

        # Error context for retries
        error_context = ""
        if task.last_error:
            error_context = f"\n## Previous Attempt Failed\n{task.last_error}\n\nPlease fix the issues and try again.\n"

        # Combine all parts
        prompt = f"""{system_prompt}

{task_spec}

{files_context}

{related_context}

{error_context}

## Instructions

Generate the code needed to complete this task. Provide your response in the following format:

```language
// Your code here
```

Explain your approach and any important decisions.
"""

        return prompt

    async def _call_llm(self, task: Task, prompt: str) -> tuple[LLMRequest, LLMResponse]:
        """
        Make an API call to the LLM.

        Args:
            task: Task being executed
            prompt: Prompt to send

        Returns:
            Tuple of (request, response)

        Raises:
            CodexExecutorError: If API call fails
        """
        request = LLMRequest(
            task_id=task.id,
            model=self.config.llm.model,
            temperature=self.config.llm.temperature,
            max_tokens=self.config.llm.max_tokens_per_request,
        )

        start_time = datetime.utcnow()

        try:
            # Call OpenAI API
            response = await self.client.chat.completions.create(
                model=self.config.llm.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.config.llm.temperature,
                max_tokens=self.config.llm.max_tokens_per_request,
                timeout=self.config.llm.timeout_seconds,
            )

            # Extract response
            completion = response.choices[0]
            content = completion.message.content or ""

            # Update request with token usage
            if response.usage:
                request.prompt_tokens = response.usage.prompt_tokens
                request.completion_tokens = response.usage.completion_tokens
                request.total_tokens = response.usage.total_tokens

            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            request.duration_ms = duration_ms
            request.success = True

            llm_response = LLMResponse(
                request_id=request.id,
                content=content,
                finish_reason=completion.finish_reason or "stop",
                cached=False,
                metadata={
                    "model": response.model,
                    "usage": response.usage.model_dump() if response.usage else {},
                },
            )

            logger.info(
                f"LLM call successful for task {task.id}: "
                f"{request.total_tokens} tokens in {duration_ms}ms"
            )

            return request, llm_response

        except OpenAIError as e:
            request.success = False
            request.error = str(e)
            logger.error(f"LLM call failed for task {task.id}: {e}")
            raise CodexExecutorError(f"LLM API error: {e}") from e

        except Exception as e:
            request.success = False
            request.error = str(e)
            logger.error(f"Unexpected error in LLM call for task {task.id}: {e}")
            raise CodexExecutorError(f"Unexpected error: {e}") from e

    def _get_cache_key(self, prompt: str, model: str) -> str:
        """
        Generate a cache key for a prompt.

        Args:
            prompt: Prompt text
            model: Model identifier

        Returns:
            Cache key (hash)
        """
        content = f"{model}:{prompt}"
        return hashlib.sha256(content.encode()).hexdigest()

    def _get_from_cache(self, cache_key: str) -> Optional[str]:
        """
        Get a cached response.

        Args:
            cache_key: Cache key

        Returns:
            Cached content or None
        """
        cache_file = self.cache_dir / f"{cache_key}.json"

        if not cache_file.exists():
            return None

        try:
            with open(cache_file) as f:
                data = json.load(f)
                return data.get("content")
        except Exception as e:
            logger.warning(f"Failed to read cache file {cache_file}: {e}")
            return None

    def _save_to_cache(self, cache_key: str, content: str) -> None:
        """
        Save a response to cache.

        Args:
            cache_key: Cache key
            content: Content to cache
        """
        cache_file = self.cache_dir / f"{cache_key}.json"

        try:
            with open(cache_file, "w") as f:
                json.dump(
                    {"content": content, "cached_at": datetime.utcnow().isoformat()}, f, indent=2
                )
        except Exception as e:
            logger.warning(f"Failed to write cache file {cache_file}: {e}")

    def extract_code_blocks(self, content: str) -> list[dict[str, str]]:
        """
        Extract code blocks from LLM response.

        Args:
            content: LLM response content

        Returns:
            List of code blocks with language and code
        """
        import re

        # Pattern to match code blocks
        pattern = r"```(\w+)?\n(.*?)```"
        matches = re.findall(pattern, content, re.DOTALL)

        code_blocks = []
        for language, code in matches:
            code_blocks.append({"language": language or "text", "code": code.strip()})

        return code_blocks

    async def validate_response(self, response: str, task: Task) -> tuple[bool, Optional[str]]:
        """
        Validate an LLM response.

        Args:
            response: LLM response content
            task: Task that was executed

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check if response contains code
        code_blocks = self.extract_code_blocks(response)

        if not code_blocks:
            return False, "Response does not contain any code blocks"

        # Additional validation based on task type
        # TODO: Add task-specific validation

        return True, None
