"""Ollama LLM provider implementation."""

import asyncio
import json
import logging
from typing import Any, AsyncIterator, Dict, Optional

import httpx
import tiktoken

from backend.config import settings
from backend.core.llm_provider import LLMConfig, LLMProvider, LLMProviderError, LLMResponse

logger = logging.getLogger(__name__)


class OllamaProvider(LLMProvider):
    """Ollama LLM provider implementation.

    This provider connects to a local Ollama instance running on the default
    port (11434) or a custom base URL. Ollama supports various open-source
    models like Llama, Mistral, CodeLlama, etc.

    Args:
        model: Name of the Ollama model to use (defaults to OLLAMA_MODEL env var or "qwen3vl:4b")
        base_url: Base URL for Ollama API (defaults to LLM_BASE_URL env var or "http://localhost:11434")
        timeout: Request timeout in seconds (default: 300)
        tokenizer_model: Encoding name or model name for tiktoken tokenizer
            (default: "cl100k_base", which is used by GPT-3.5-turbo and GPT-4)
    """

    def __init__(
        self,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: int = 300,
        tokenizer_model: str = "cl100k_base",
    ) -> None:
        """Initialize Ollama provider.

        Args:
            model: Name of the Ollama model to use (defaults to OLLAMA_MODEL env var or "qwen3vl:4b")
            base_url: Base URL for Ollama API (defaults to LLM_BASE_URL env var or "http://localhost:11434")
            timeout: Request timeout in seconds
            tokenizer_model: Encoding name or model name for tiktoken tokenizer
                (default: "cl100k_base", which is used by GPT-3.5-turbo and GPT-4)
        """
        # Use provided model, or fall back to environment variable, or default
        self.model = model or settings.ollama_model
        # Use provided base_url, or fall back to environment variable, or default
        self.base_url = (base_url or settings.llm_base_url).rstrip("/")
        self.timeout = timeout
        self.tokenizer_model = tokenizer_model
        self._tokenizer: Optional[tiktoken.Encoding] = None
        self._client: Optional[httpx.AsyncClient] = None
        self._sync_client: Optional[httpx.Client] = None

    @property
    def client(self) -> httpx.AsyncClient:
        """Lazy-load async HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
            )
        return self._client

    @property
    def sync_client(self) -> httpx.Client:
        """Lazy-load sync HTTP client."""
        if self._sync_client is None:
            self._sync_client = httpx.Client(
                base_url=self.base_url,
                timeout=self.timeout,
            )
        return self._sync_client

    @property
    def tokenizer(self) -> tiktoken.Encoding:
        """Lazy-load tokenizer for token counting."""
        if self._tokenizer is None:
            try:
                # Try to get encoding directly (faster, no model lookup)
                self._tokenizer = tiktoken.get_encoding(self.tokenizer_model)
            except KeyError:
                # Fallback: try encoding_for_model if it's a model name
                try:
                    self._tokenizer = tiktoken.encoding_for_model(self.tokenizer_model)
                except KeyError:
                    # Final fallback to cl100k_base
                    logger.warning(f"Tokenizer model/encoding {self.tokenizer_model} not found, using cl100k_base")
                    self._tokenizer = tiktoken.get_encoding("cl100k_base")
        return self._tokenizer

    def _build_prompt(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Build the full prompt from user and system prompts.

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt

        Returns:
            str: Combined prompt
        """
        if system_prompt:
            return f"{system_prompt}\n\n{prompt}"
        return prompt

    def _build_request_data(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        config: Optional[LLMConfig] = None,
        stream: bool = False,
    ) -> Dict[str, Any]:
        """Build request data for Ollama API.

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            config: Optional generation configuration
            stream: Whether to stream the response

        Returns:
            Dict[str, Any]: Request data for Ollama API
        """
        request_data: Dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": stream,
        }

        if system_prompt:
            request_data["system"] = system_prompt

        # Build options dict for Ollama
        options: Dict[str, Any] = {}

        if config:
            if config.temperature is not None:
                options["temperature"] = config.temperature
            if config.top_p is not None:
                options["top_p"] = config.top_p
            if config.max_tokens is not None:
                # Ollama uses "num_predict" instead of "max_tokens"
                options["num_predict"] = config.max_tokens
            if config.stop is not None:
                options["stop"] = config.stop
            # Ollama doesn't support frequency_penalty or presence_penalty directly
            # but we can include them in extra_params if needed
            if config.extra_params:
                options.update(config.extra_params)

        if options:
            request_data["options"] = options

        return request_data

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        config: Optional[LLMConfig] = None,
    ) -> LLMResponse:
        """Generate text from a prompt synchronously.

        Args:
            prompt: The user prompt/message to send to the model
            system_prompt: Optional system prompt to set model behavior
            config: Optional configuration for generation parameters

        Returns:
            LLMResponse: Response containing generated text and metadata

        Raises:
            LLMProviderError: If generation fails
        """
        self.validate_config(config)

        request_data = self._build_request_data(prompt, system_prompt, config, stream=False)

        try:
            response = self.sync_client.post("/api/generate", json=request_data)
            response.raise_for_status()
            result = response.json()
        except httpx.HTTPError as e:
            logger.error(f"Ollama API request failed: {e}")
            raise LLMProviderError(f"Failed to generate text: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error during Ollama generation: {e}")
            raise LLMProviderError(f"Unexpected error during generation: {e}") from e

        # Extract response text
        response_text = result.get("response", "")

        # Count tokens
        full_prompt = self._build_prompt(prompt, system_prompt)
        prompt_tokens = self.count_tokens(full_prompt)
        completion_tokens = self.count_tokens(response_text)
        total_tokens = prompt_tokens + completion_tokens

        # Extract metadata
        metadata = {
            "done": result.get("done", False),
            "context": result.get("context", []),
            "total_duration": result.get("total_duration", 0),
            "load_duration": result.get("load_duration", 0),
            "prompt_eval_count": result.get("prompt_eval_count", 0),
            "prompt_eval_duration": result.get("prompt_eval_duration", 0),
            "eval_count": result.get("eval_count", 0),
            "eval_duration": result.get("eval_duration", 0),
        }

        return LLMResponse(
            text=response_text,
            model=self.model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            metadata=metadata,
        )

    async def generate_async(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        config: Optional[LLMConfig] = None,
    ) -> LLMResponse:
        """Generate text from a prompt asynchronously.

        Args:
            prompt: The user prompt/message to send to the model
            system_prompt: Optional system prompt to set model behavior
            config: Optional configuration for generation parameters

        Returns:
            LLMResponse: Response containing generated text and metadata

        Raises:
            LLMProviderError: If generation fails
        """
        self.validate_config(config)

        request_data = self._build_request_data(prompt, system_prompt, config, stream=False)

        try:
            response = await self.client.post("/api/generate", json=request_data)
            response.raise_for_status()
            result = response.json()
        except httpx.HTTPError as e:
            logger.error(f"Ollama API request failed: {e}")
            raise LLMProviderError(f"Failed to generate text: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error during Ollama generation: {e}")
            raise LLMProviderError(f"Unexpected error during generation: {e}") from e

        # Extract response text
        response_text = result.get("response", "")

        # Count tokens
        full_prompt = self._build_prompt(prompt, system_prompt)
        prompt_tokens = self.count_tokens(full_prompt)
        completion_tokens = self.count_tokens(response_text)
        total_tokens = prompt_tokens + completion_tokens

        # Extract metadata
        metadata = {
            "done": result.get("done", False),
            "context": result.get("context", []),
            "total_duration": result.get("total_duration", 0),
            "load_duration": result.get("load_duration", 0),
            "prompt_eval_count": result.get("prompt_eval_count", 0),
            "prompt_eval_duration": result.get("prompt_eval_duration", 0),
            "eval_count": result.get("eval_count", 0),
            "eval_duration": result.get("eval_duration", 0),
        }

        return LLMResponse(
            text=response_text,
            model=self.model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            metadata=metadata,
        )

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        config: Optional[LLMConfig] = None,
    ) -> AsyncIterator[str]:
        """Generate text from a prompt with streaming response.

        Args:
            prompt: The user prompt/message to send to the model
            system_prompt: Optional system prompt to set model behavior
            config: Optional configuration for generation parameters

        Yields:
            str: Text chunks as they are generated

        Raises:
            LLMProviderError: If generation fails
        """
        self.validate_config(config)

        request_data = self._build_request_data(prompt, system_prompt, config, stream=True)

        try:
            async with self.client.stream("POST", "/api/generate", json=request_data) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue

                    try:
                        chunk_data = json.loads(line)
                    except (json.JSONDecodeError, ValueError):
                        # If line is not valid JSON, skip it
                        continue

                    # Extract text chunk
                    if "response" in chunk_data:
                        yield chunk_data["response"]

                    # Check if done
                    if chunk_data.get("done", False):
                        break

        except httpx.HTTPError as e:
            logger.error(f"Ollama streaming request failed: {e}")
            raise LLMProviderError(f"Failed to stream text") from e
        except Exception as e:
            logger.error(f"Unexpected error during Ollama streaming: {e}")
            raise LLMProviderError(f"Unexpected error during streaming: {e}") from e

    def count_tokens(self, text: str) -> int:
        """Count the number of tokens in a text string.

        Args:
            text: Text to count tokens for

        Returns:
            int: Number of tokens in the text

        Raises:
            LLMProviderError: If token counting fails
        """
        if not text:
            return 0

        try:
            return len(self.tokenizer.encode(text))
        except Exception as e:
            logger.error(f"Token counting failed: {e}")
            raise LLMProviderError(f"Failed to count tokens: {e}") from e

    def get_model_name(self) -> str:
        """Get the name of the model being used.

        Returns:
            str: Model name/identifier
        """
        return self.model

    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the model.

        Returns:
            Dict[str, Any]: Model information (name, context length, etc.)
        """
        return {
            "provider": "ollama",
            "model": self.model,
            "base_url": self.base_url,
            "tokenizer_model": self.tokenizer_model,
        }

    def __del__(self) -> None:
        """Cleanup resources on deletion."""
        if self._client is not None:
            try:
                asyncio.create_task(self._client.aclose())
            except Exception:
                pass

        if self._sync_client is not None:
            try:
                self._sync_client.close()
            except Exception:
                pass
