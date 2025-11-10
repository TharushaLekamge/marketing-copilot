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
    build_rag_context,
    get_content_generation_system_prompt,
)
from backend.core.semantic_search import SemanticSearchOrchestrator
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
        objective: Optional[str] = None,
        asset_summaries: Optional[list] = None,
        use_rag: bool = True,
        rag_top_k: int = 5,
    ) -> Dict[str, Any]:
        """Generate content variants (short-form, long-form, CTA).

        Args:
            brief: Campaign brief or description
            project_id: Optional project ID for tracking and RAG context retrieval
            project_name: Optional project name for context
            project_description: Optional project description for context
            brand_tone: Optional brand tone and style guidelines
            objective: Optional campaign objective
            asset_summaries: Optional list of asset summaries for context
            use_rag: Whether to use RAG to retrieve relevant chunks from ingested assets (default: True)
            rag_top_k: Number of relevant chunks to retrieve when using RAG (default: 5)

        Returns:
            Dict containing:
                - short_form: Short-form content variant
                - long_form: Long-form content variant
                - cta: CTA-focused content variant
                - metadata: Generation metadata (tokens, model, chunks_retrieved, etc.)

        Raises:
            GenerationError: If generation fails
        """
        try:
            # Build base project context (name, description, asset list)
            project_context = build_project_context(
                project_name=project_name,
                project_description=project_description,
                asset_summaries=asset_summaries,
            )

            # Build combined query for RAG using both brief and objective
            rag_query_parts = [brief]
            if objective:
                rag_query_parts.append(objective)
            rag_query = " ".join(rag_query_parts)

            # Retrieve relevant chunks using semantic search if RAG is enabled
            rag_context = ""
            chunks_retrieved = 0
            logger.info(f"use_rag: {use_rag}, project_id: {project_id}")
            if use_rag and project_id:
                try:
                    logger.info(f"Retrieving relevant chunks for generation query: {rag_query[:50]}...")
                    semantic_search = SemanticSearchOrchestrator()
                    search_results = await semantic_search.search_with_context(
                        query=rag_query,  # Use combined brief + objective as search query
                        project_id=project_id,
                        top_k=rag_top_k,
                        include_metadata=True,
                    )
                    

                    if search_results:
                        chunks_retrieved = len(search_results)
                        rag_context = build_rag_context(search_results)
                        logger.info(f"Retrieved {chunks_retrieved} relevant chunks for generation")
                    else:
                        logger.info("No relevant chunks found for generation query")
                except Exception as e:
                    logger.warning(f"RAG context retrieval failed: {e}, continuing without RAG context")
                    # Continue without RAG context if retrieval fails

            # Merge RAG context with project context
            if rag_context:
                if project_context:
                    full_context = f"{project_context}\n\nRelevant Content from Project Documents:\n{rag_context}"
                else:
                    full_context = f"Relevant Content from Project Documents:\n{rag_context}"
            else:
                full_context = project_context

            # Build enhanced brief with objective for content generation
            enhanced_brief = brief
            if objective:
                enhanced_brief = f"{brief}\n\nObjective: {objective}"

            # Get system prompt with merged context
            system_prompt = get_content_generation_system_prompt(
                brand_tone=brand_tone,
                project_context=full_context if full_context else None,
            )

            # Prepare arguments for Semantic Kernel
            args = KernelArguments(
                system_message=system_prompt,
                brief=enhanced_brief,  # Include objective in brief
                brand_tone=brand_tone or "",
                context=full_context or "",
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
                "chunks_retrieved": chunks_retrieved if use_rag and project_id else None,
                "rag_enabled": use_rag and project_id is not None,
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
    objective: Optional[str] = None,
    asset_summaries: Optional[list] = None,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    use_rag: bool = True,
    rag_top_k: int = 5,
) -> Dict[str, Any]:
    """Generate content variants using Semantic Kernel orchestration.

    This is a convenience function that creates an orchestrator and generates variants.

    Args:
        brief: Campaign brief or description
        project_id: Optional project ID for tracking and RAG context retrieval
        project_name: Optional project name for context
        project_description: Optional project description for context
        brand_tone: Optional brand tone and style guidelines
        objective: Optional campaign objective
        asset_summaries: Optional list of asset summaries for context
        api_key: Optional OpenAI API key (defaults to settings.openai_api_key)
        model: Optional OpenAI model name (defaults to settings.openai_chat_model_id)
        use_rag: Whether to use RAG to retrieve relevant chunks from ingested assets (default: True)
        rag_top_k: Number of relevant chunks to retrieve when using RAG (default: 5)

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
        objective=objective,
        asset_summaries=asset_summaries,
        use_rag=use_rag,
        rag_top_k=rag_top_k,
    )
