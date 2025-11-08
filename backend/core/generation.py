"""Content generation orchestration using Semantic Kernel."""

import logging
from typing import Any, Dict, Optional
from uuid import UUID

from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.ollama import OllamaChatCompletion
from semantic_kernel.contents import ChatHistory
from semantic_kernel.functions import KernelArguments
from semantic_kernel.prompt_template import PromptTemplateConfig

from backend.config import settings
from backend.core.prompt_templates import (
    build_project_context,
    get_content_generation_system_prompt,
)
from backend.core.sk_plugins.content_generation import (
    CTA_TEMPLATE,
    LONG_FORM_TEMPLATE,
    SHORT_FORM_TEMPLATE,
)

logger = logging.getLogger(__name__)


class GenerationError(Exception):
    """Exception raised during content generation."""

    pass


class ContentGenerationOrchestrator:
    """Orchestrates content generation using Semantic Kernel."""

    def __init__(self, base_url: Optional[str] = None, model: Optional[str] = None):
        """Initialize the orchestrator with Ollama configuration.

        Args:
            base_url: Ollama base URL (defaults to LLM_BASE_URL from settings)
            model: Ollama model name (defaults to OLLAMA_MODEL from settings)
        """
        self.kernel = Kernel()
        self.base_url = base_url or settings.llm_base_url
        self.model = model or settings.ollama_model

        # Use Semantic Kernel's native OllamaChatCompletion
        ollama_service = OllamaChatCompletion(
            host=self.base_url,
            ai_model_id=self.model,
        )
        self.kernel.add_service(ollama_service)

        # Create prompt template config (reusable)
        prompt_config = PromptTemplateConfig(
            template_format="handlebars",
        )

        # Register functions once during initialization (reusable)
        self.short_form_func = self.kernel.add_function(
            function_name="generate_short_form",
            plugin_name="ContentGeneration",
            prompt=SHORT_FORM_TEMPLATE,
            prompt_template_config=prompt_config,
        )

        self.long_form_func = self.kernel.add_function(
            function_name="generate_long_form",
            plugin_name="ContentGeneration",
            prompt=LONG_FORM_TEMPLATE,
            prompt_template_config=prompt_config,
        )

        self.cta_func = self.kernel.add_function(
            function_name="generate_cta",
            plugin_name="ContentGeneration",
            prompt=CTA_TEMPLATE,
            prompt_template_config=prompt_config,
        )

    async def generate_variants(
        self,
        brief: str,
        project_id: Optional[UUID] = None,
        project_name: Optional[str] = None,
        project_description: Optional[str] = None,
        brand_tone: Optional[str] = None,
        asset_summaries: Optional[list] = None,
    ) -> Dict[str, Any]:
        """Generate content variants (short-form, long-form, CTA).

        Args:
            brief: Campaign brief or description
            project_id: Optional project ID for tracking
            project_name: Optional project name for context
            project_description: Optional project description for context
            brand_tone: Optional brand tone and style guidelines
            asset_summaries: Optional list of asset summaries for context

        Returns:
            Dict containing:
                - short_form: Short-form content variant
                - long_form: Long-form content variant
                - cta: CTA-focused content variant
                - metadata: Generation metadata (tokens, model, etc.)

        Raises:
            GenerationError: If generation fails
        """
        try:
            # Build project context
            project_context = build_project_context(
                project_name=project_name,
                project_description=project_description,
                asset_summaries=asset_summaries,
            )

            # Get system prompt
            system_prompt = get_content_generation_system_prompt(
                brand_tone=brand_tone,
                project_context=project_context if project_context else None,
            )

            # Prepare arguments for Semantic Kernel
            args = KernelArguments(
                brief=brief,
                brand_tone=brand_tone or "",
                context=project_context or "",
            )

            # Create chat history with system prompt
            chat_history = ChatHistory()
            chat_history.add_system_message(system_prompt)

            # Invoke pre-registered functions (reused from __init__)
            short_form_result = await self.kernel.invoke(
                function=self.short_form_func,
                arguments=args,
                chat_history=chat_history,
            )

            long_form_result = await self.kernel.invoke(
                function=self.long_form_func,
                arguments=args,
                chat_history=chat_history,
            )

            cta_result = await self.kernel.invoke(
                function=self.cta_func,
                arguments=args,
                chat_history=chat_history,
            )

            # Extract results
            short_form = str(short_form_result.value).strip()
            long_form = str(long_form_result.value).strip()
            cta = str(cta_result.value).strip()

            # Get metadata
            metadata = {
                "model": self.model,
                "base_url": self.base_url,
                "project_id": str(project_id) if project_id else None,
            }

            return {
                "short_form": short_form,
                "long_form": long_form,
                "cta": cta,
                "metadata": metadata,
            }

        except Exception as e:
            logger.error(f"Error generating content variants: {e}", exc_info=True)
            raise GenerationError(f"Failed to generate content variants: {e}") from e


async def generate_content_variants(
    brief: str,
    project_id: Optional[UUID] = None,
    project_name: Optional[str] = None,
    project_description: Optional[str] = None,
    brand_tone: Optional[str] = None,
    asset_summaries: Optional[list] = None,
    base_url: Optional[str] = None,
    model: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate content variants using Semantic Kernel orchestration.

    This is a convenience function that creates an orchestrator and generates variants.

    Args:
        brief: Campaign brief or description
        project_id: Optional project ID for tracking
        project_name: Optional project name for context
        project_description: Optional project description for context
        brand_tone: Optional brand tone and style guidelines
        asset_summaries: Optional list of asset summaries for context
        base_url: Optional Ollama base URL (defaults to LLM_BASE_URL from settings)
        model: Optional Ollama model name (defaults to OLLAMA_MODEL from settings)

    Returns:
        Dict containing variants and metadata

    Raises:
        GenerationError: If generation fails
    """
    orchestrator = ContentGenerationOrchestrator(base_url=base_url, model=model)
    return await orchestrator.generate_variants(
        brief=brief,
        project_id=project_id,
        project_name=project_name,
        project_description=project_description,
        brand_tone=brand_tone,
        asset_summaries=asset_summaries,
    )
