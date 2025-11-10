"""RAG (Retrieval-Augmented Generation) pipeline orchestration using Semantic Kernel."""

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion
from semantic_kernel.functions import KernelArguments, KernelFunctionFromPrompt
from semantic_kernel.connectors.ai.open_ai import OpenAIChatPromptExecutionSettings

from backend.config import settings
from backend.core.prompt_templates import build_rag_context, get_assistant_system_prompt
from backend.core.semantic_search import SemanticSearchError, SemanticSearchOrchestrator
from backend.core.sk_plugins.assistant import ASSISTANT_TEMPLATE

logger = logging.getLogger(__name__)


class RAGError(Exception):
    """Exception raised during RAG pipeline execution."""

    pass


class RAGOrchestrator:
    """Orchestrates RAG pipeline using Semantic Kernel and semantic search."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        semantic_search_orchestrator: Optional[SemanticSearchOrchestrator] = None,
    ):
        """Initialize the RAG orchestrator.

        Args:
            api_key: OpenAI API key (defaults to settings.openai_api_key)
            model: OpenAI model name (defaults to settings.openai_chat_model_id)
            semantic_search_orchestrator: Optional semantic search orchestrator instance
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

        # Create execution settings
        execution_settings = OpenAIChatPromptExecutionSettings()
        execution_settings.max_tokens = 1000  # Allow longer responses for assistant

        # Register assistant function
        self.assistant_func = KernelFunctionFromPrompt(
            function_name="assistant_query",
            prompt=ASSISTANT_TEMPLATE,
            template_format="handlebars",
            prompt_execution_settings=execution_settings,
        )

        # Semantic search orchestrator
        self.semantic_search = semantic_search_orchestrator or SemanticSearchOrchestrator()

    async def query(
        self,
        question: str,
        project_id: UUID,
        top_k: int = 5,
        include_citations: bool = True,
    ) -> Dict[str, Any]:
        """Process a query through the RAG pipeline.

        Args:
            question: User's question
            project_id: Project ID to search within
            top_k: Number of relevant chunks to retrieve
            include_citations: Whether to include citations in response

        Returns:
            Dict containing:
                - answer: Generated answer from LLM
                - citations: List of citation dictionaries with source info
                - metadata: RAG metadata (model, tokens, etc.)

        Raises:
            RAGError: If RAG pipeline fails
        """
        try:
            if not question or not question.strip():
                logger.warning("Empty question provided to RAG pipeline")
                raise RAGError("Question cannot be empty")

            # Step 1: Retrieve relevant chunks using semantic search
            logger.debug(f"Retrieving relevant chunks for question: {question[:50]}...")
            search_results = await self.semantic_search.search_with_context(
                query=question,
                project_id=project_id,
                top_k=top_k,
                include_metadata=True,
            )

            if not search_results:
                logger.info("No relevant chunks found for question")
                # Still generate a response, but acknowledge no context
                context = ""
            else:
                # Step 2: Build context string from retrieved chunks
                logger.debug(f"Building context from {len(search_results)} chunks")
                context = build_rag_context(search_results)

            # Step 3: Get system prompt
            system_prompt = get_assistant_system_prompt()

            # Step 4: Prepare arguments for Semantic Kernel
            args = KernelArguments(
                system_message=system_prompt,
                question=question.strip(),
                context=context if context else "No relevant context found in project documents.",
            )

            # Step 5: Invoke LLM with context
            logger.debug("Invoking LLM with RAG context")
            result = await self.kernel.invoke(
                function=self.assistant_func,
                arguments=args,
            )

            # Step 6: Extract answer from LLM response
            answer = str(result.value[0].content) if result and result.value and len(result.value) > 0 else ""

            if not answer:
                raise RAGError("LLM returned empty response")

            # Step 7: Extract citations from search results
            citations = []
            if include_citations and search_results:
                for i, result in enumerate(search_results, 1):
                    citation = {
                        "index": i,
                        "text": result.get("text", ""),
                        "asset_id": result.get("asset_id", ""),
                        "chunk_index": result.get("chunk_index", 0),
                        "score": result.get("score", 0.0),
                    }
                    # Add metadata if available
                    if result.get("metadata"):
                        citation["metadata"] = result.get("metadata")
                    citations.append(citation)

            # Step 8: Build metadata
            metadata = {
                "model": self.model,
                "provider": "openai",
                "project_id": str(project_id),
                "chunks_retrieved": len(search_results),
                "has_context": len(search_results) > 0,
            }

            logger.info(f"RAG query completed for project {project_id}, retrieved {len(search_results)} chunks")

            return {
                "answer": answer,
                "citations": citations,
                "metadata": metadata,
            }

        except SemanticSearchError as e:
            logger.error(f"Semantic search error in RAG pipeline: {e}")
            raise RAGError(f"Failed to retrieve context: {e}") from e
        except Exception as e:
            logger.error(f"Error in RAG pipeline: {e}", exc_info=True)
            raise RAGError(f"RAG pipeline failed: {e}") from e


async def rag_query(
    question: str,
    project_id: UUID,
    top_k: int = 5,
    include_citations: bool = True,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    semantic_search_orchestrator: Optional[SemanticSearchOrchestrator] = None,
) -> Dict[str, Any]:
    """Process a query through the RAG pipeline (convenience function).

    This is a convenience function that creates an orchestrator and processes the query.

    Args:
        question: User's question
        project_id: Project ID to search within
        top_k: Number of relevant chunks to retrieve
        include_citations: Whether to include citations in response
        api_key: Optional OpenAI API key
        model: Optional OpenAI model name
        semantic_search_orchestrator: Optional semantic search orchestrator instance

    Returns:
        Dict containing answer, citations, and metadata

    Raises:
        RAGError: If RAG pipeline fails
    """
    orchestrator = RAGOrchestrator(
        api_key=api_key,
        model=model,
        semantic_search_orchestrator=semantic_search_orchestrator,
    )
    return await orchestrator.query(
        question=question,
        project_id=project_id,
        top_k=top_k,
        include_citations=include_citations,
    )
