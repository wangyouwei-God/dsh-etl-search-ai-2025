"""
Chat Router - RAG and Conversational API Endpoints

This module provides the chat endpoints for RAG-based question answering
and multi-turn conversation support.

Author: University of Manchester RSE Team
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends

from api.models import (
    ChatRequestSchema,
    ChatResponseSchema,
    ChatSourceSchema,
    ConversationSchema
)
from application.services.rag_service import RAGService, RAGContext

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/chat", tags=["Chat"])

# Global RAG service (will be set by main.py)
rag_service: Optional[RAGService] = None


def get_rag_service() -> RAGService:
    """Dependency to get RAG service."""
    if rag_service is None:
        raise HTTPException(
            status_code=503, 
            detail="RAG service not initialized. Check if Gemini API key is configured."
        )
    return rag_service


def context_to_source_schema(ctx: RAGContext) -> ChatSourceSchema:
    """Convert RAGContext to ChatSourceSchema."""
    return ChatSourceSchema(
        id=ctx.source_id,
        title=ctx.title,
        source_type=ctx.source_type,
        relevance_score=ctx.relevance_score,
        content_preview=ctx.content[:200] if ctx.content else None
    )


@router.post("", response_model=ChatResponseSchema)
async def chat(
    request: ChatRequestSchema,
    service: RAGService = Depends(get_rag_service)
):
    """
    Chat endpoint for RAG-based question answering.
    
    Supports multi-turn conversations with context retrieval from datasets.
    
    Args:
        request: Chat request containing message and optional conversation_id
        
    Returns:
        ChatResponseSchema with answer, sources, and conversation_id
    """
    try:
        logger.info(f"Chat request: message='{request.message[:50]}...'")
        
        # Execute RAG query with conversation support
        response = service.chat(
            message=request.message,
            conversation_id=request.conversation_id,
            include_sources=request.include_sources
        )
        
        # Convert sources to API schema
        sources = [context_to_source_schema(ctx) for ctx in response.sources]
        
        logger.info(
            f"Chat response: {len(response.answer)} chars, "
            f"{len(sources)} sources, {response.processing_time_ms:.0f}ms"
        )
        
        return ChatResponseSchema(
            answer=response.answer,
            conversation_id=response.conversation_id,
            sources=sources,
            processing_time_ms=response.processing_time_ms
        )
        
    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


@router.get("/conversations", response_model=list[ConversationSchema])
async def list_conversations(
    service: RAGService = Depends(get_rag_service)
):
    """
    List all active conversations.
    
    Returns:
        List of active conversations with basic metadata
    """
    try:
        conversations = service.list_conversations()
        return [
            ConversationSchema(
                id=c["id"],
                turns_count=c["turns"],
                created_at=c["created_at"],
                updated_at=c["updated_at"]
            )
            for c in conversations
        ]
    except Exception as e:
        logger.error(f"List conversations error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    service: RAGService = Depends(get_rag_service)
):
    """
    Delete a conversation.
    
    Args:
        conversation_id: ID of conversation to delete
        
    Returns:
        Success message
    """
    try:
        if service.delete_conversation(conversation_id):
            return {"message": f"Conversation {conversation_id} deleted"}
        else:
            raise HTTPException(status_code=404, detail="Conversation not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete conversation error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/conversations/{conversation_id}/clear")
async def clear_conversation(
    conversation_id: str,
    service: RAGService = Depends(get_rag_service)
):
    """
    Clear conversation history but keep the conversation.
    
    Args:
        conversation_id: ID of conversation to clear
        
    Returns:
        Success message
    """
    try:
        if service.clear_conversation(conversation_id):
            return {"message": f"Conversation {conversation_id} cleared"}
        else:
            raise HTTPException(status_code=404, detail="Conversation not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Clear conversation error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
