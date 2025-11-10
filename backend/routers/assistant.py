"""Assistant/RAG router."""

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.core.dependencies import get_current_user
from backend.core.rag_pipeline import RAGError, RAGOrchestrator
from backend.database import get_db
from backend.models.project import Project
from backend.models.user import User
from backend.schemas.assistant import AssistantQueryRequest, AssistantQueryResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/assistant", tags=["assistant"])


@router.post("/query", response_model=AssistantQueryResponse, status_code=status.HTTP_200_OK)
async def query_assistant(
    query_request: AssistantQueryRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> AssistantQueryResponse:
    """Query the assistant with RAG (Retrieval-Augmented Generation).

    This endpoint uses semantic search to retrieve relevant context from the user's
    project documents and generates an answer using an LLM.

    Args:
        query_request: Assistant query request with project_id and question
        current_user: Current authenticated user
        db: Database session

    Returns:
        AssistantQueryResponse: Answer with citations and metadata

    Raises:
        HTTPException: If project not found, user doesn't own project, or RAG fails
    """
    # Validate project exists and user owns it
    project = db.query(Project).filter(Project.id == query_request.project_id).first()

    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    if project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to query assistant for this project",
        )

    try:
        # Create RAG orchestrator
        orchestrator = RAGOrchestrator()

        # Process query through RAG pipeline
        result = await orchestrator.query(
            question=query_request.question,
            project_id=query_request.project_id,
            top_k=query_request.top_k,
            include_citations=query_request.include_citations,
        )

        logger.info(
            f"Assistant query processed for project {query_request.project_id} "
            f"by user {current_user.id}, retrieved {result['metadata']['chunks_retrieved']} chunks"
        )

        return AssistantQueryResponse(**result)

    except RAGError as e:
        logger.error(f"RAG error processing query: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process query: {e}",
        ) from e
    except Exception as e:
        logger.error(f"Unexpected error processing assistant query: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while processing your query",
        ) from e
