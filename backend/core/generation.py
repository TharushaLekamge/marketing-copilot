"""Content generation orchestration using Semantic Kernel."""

import asyncio
import logging
from typing import Any, Dict, Optional
from uuid import UUID

import semantic_kernel
from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion
from semantic_kernel.contents import AuthorRole, ChatHistory, ChatMessageContent
from semantic_kernel.functions import KernelArguments, KernelFunctionFromPrompt
from semantic_kernel.connectors.ai.open_ai import OpenAIChatPromptExecutionSettings

# print version of semantic kernel

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

logger.info(f"Semantic Kernel version: {semantic_kernel.__version__}")


class GenerationError(Exception):
    """Exception raised during content generation."""

    pass


class ContentGenerationOrchestrator:
    """Orchestrates content generation using Semantic Kernel."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """Initialize the orchestrator with OpenAI configuration.

        Args:
            api_key: OpenAI API key (defaults to settings.openai_api_key)
            model: OpenAI model name (defaults to settings.openai_chat_model_id)
        """
        self.kernel = Kernel()
        self.api_key = api_key or settings.openai_api_key
        self.model = model or settings.openai_chat_model_id or "gpt-4o"

        # Use Semantic Kernel's native OpenAIChatCompletion
        openai_service = OpenAIChatCompletion(
            api_key=self.api_key,
            ai_model_id=self.model,
        )
        self.kernel.add_service(openai_service)

        # Create execution settings with max tokens limit for testing
        execution_settings = OpenAIChatPromptExecutionSettings()
        execution_settings.max_tokens = 150

        # Register functions once during initialization (reusable)
        self.short_form_func = KernelFunctionFromPrompt(
            function_name="generate_short_form",
            prompt=SHORT_FORM_TEMPLATE,
            template_format="handlebars",
            prompt_execution_settings=execution_settings,
        )

        self.long_form_func = KernelFunctionFromPrompt(
            function_name="generate_long_form",
            prompt=LONG_FORM_TEMPLATE,
            template_format="handlebars",
            prompt_execution_settings=execution_settings,
        )

        self.cta_func = KernelFunctionFromPrompt(
            function_name="generate_cta",
            prompt=CTA_TEMPLATE,
            template_format="handlebars",
            prompt_execution_settings=execution_settings,
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
                system_message=system_prompt,
                brief=brief,
                brand_tone=brand_tone or "",
                context=project_context or "",
            )

            # Generate short-form content
            short_form_result = await self.kernel.invoke(
                function=self.short_form_func,
                arguments=args,
            )

            # Generate long-form content
            long_form_result = await self.kernel.invoke(
                function=self.long_form_func,
                arguments=args,
            )

            # Generate CTA content
            cta_result = await self.kernel.invoke(
                function=self.cta_func,
                arguments=args,
            )

            # Extract results from function invocations
            short_form = (
                str(short_form_result.value[0].content) if short_form_result and short_form_result.value else ""
            )
            long_form = str(long_form_result.value[0].content) if long_form_result and long_form_result.value else ""
            cta = str(cta_result.value[0].content) if cta_result and cta_result.value else ""

            # Get metadata
            metadata = {
                "model": self.model,
                "provider": "openai",
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
    api_key: Optional[str] = None,
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
        api_key: Optional OpenAI API key (defaults to settings.openai_api_key)
        model: Optional OpenAI model name (defaults to settings.openai_chat_model_id)

    Returns:
        Dict containing variants and metadata

    Raises:
        GenerationError: If generation fails
    """
    orchestrator = ContentGenerationOrchestrator(api_key=api_key, model=model)
    return await orchestrator.generate_variants(
        brief=brief,
        project_id=project_id,
        project_name=project_name,
        project_description=project_description,
        brand_tone=brand_tone,
        asset_summaries=asset_summaries,
    )
