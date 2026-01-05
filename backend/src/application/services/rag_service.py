"""
Application: RAG Service

This module provides Retrieval Augmented Generation (RAG) capabilities,
combining semantic search with LLM-based answer generation.

Author: University of Manchester RSE Team
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
from uuid import uuid4

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from domain.repositories.vector_repository import IVectorRepository, VectorSearchResult
from application.interfaces.embedding_service import IEmbeddingService
from infrastructure.services.gemini_service import GeminiService, GeminiMessage, GeminiError

logger = logging.getLogger(__name__)


@dataclass
class RAGContext:
    """Context retrieved for RAG."""
    source_id: str
    source_type: str  # 'dataset' or 'document'
    title: str
    content: str
    relevance_score: float
    metadata: Dict = field(default_factory=dict)


@dataclass
class RAGResponse:
    """Response from RAG query."""
    answer: str
    sources: List[RAGContext]
    query: str
    processing_time_ms: float
    conversation_id: Optional[str] = None


@dataclass
class ConversationTurn:
    """A single turn in a conversation."""
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    sources: List[RAGContext] = field(default_factory=list)


@dataclass
class Conversation:
    """Multi-turn conversation state."""
    id: str = field(default_factory=lambda: str(uuid4()))
    turns: List[ConversationTurn] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def add_turn(self, role: str, content: str, sources: List[RAGContext] = None):
        """Add a turn to the conversation."""
        self.turns.append(ConversationTurn(
            role=role,
            content=content,
            sources=sources or []
        ))
        self.updated_at = datetime.utcnow()
    
    def get_history(self, max_turns: int = 10) -> List[GeminiMessage]:
        """Get conversation history as Gemini messages."""
        recent_turns = self.turns[-max_turns:] if len(self.turns) > max_turns else self.turns
        return [
            GeminiMessage(role=turn.role, content=turn.content)
            for turn in recent_turns
        ]
    
    def clear(self):
        """Clear conversation history."""
        self.turns = []
        self.updated_at = datetime.utcnow()


class RAGService:
    """
    Retrieval Augmented Generation Service.
    
    This service combines:
    - Semantic search over datasets and documents
    - LLM-based answer generation
    - Multi-turn conversation support
    - Source citation
    
    Design Pattern: Facade Pattern
    - Provides simple interface for complex RAG pipeline
    - Coordinates vector search, embedding, and LLM services
    """
    
    def __init__(
        self,
        embedding_service: IEmbeddingService,
        vector_repository: IVectorRepository,
        gemini_service: GeminiService,
        supporting_docs_repository: Optional[IVectorRepository] = None,
        top_k: int = 5,
        min_relevance_score: float = 0.3,
        doc_top_k: int = 5
    ):
        """
        Initialize RAG service.
        
        Args:
            embedding_service: Service for generating embeddings
            vector_repository: Repository for vector search
            gemini_service: Gemini LLM service
            top_k: Number of documents to retrieve
            min_relevance_score: Minimum relevance score for inclusion
        """
        self.embedding_service = embedding_service
        self.vector_repository = vector_repository
        self.supporting_docs_repository = supporting_docs_repository
        self.gemini_service = gemini_service
        self.top_k = top_k
        self.min_relevance_score = min_relevance_score
        self.doc_top_k = doc_top_k
        
        # Store active conversations
        self.conversations: Dict[str, Conversation] = {}
        
        logger.info(
            f"RAGService initialized: top_k={top_k}, "
            f"min_relevance={min_relevance_score}"
        )
    
    def _retrieve_context(self, query: str) -> List[RAGContext]:
        """
        Retrieve relevant context for a query.
        
        Args:
            query: User query text
            
        Returns:
            List of relevant context items
        """
        # Generate query embedding
        query_embedding = self.embedding_service.generate_embedding(query)
        
        # Search vector database
        dataset_results = self.vector_repository.search(
            query_vector=query_embedding,
            limit=self.top_k
        )

        contexts: List[RAGContext] = []
        for result in dataset_results:
            if result.score >= self.min_relevance_score:
                contexts.append(
                    RAGContext(
                        source_id=result.id,
                        source_type=result.metadata.get("type", "dataset"),
                        title=result.metadata.get("title", "Unknown"),
                        content=result.metadata.get("abstract", ""),
                        relevance_score=result.score,
                        metadata=result.metadata
                    )
                )

        if self.supporting_docs_repository:
            doc_results = self.supporting_docs_repository.search(
                query_vector=query_embedding,
                limit=self.doc_top_k
            )
            for result in doc_results:
                if result.score >= self.min_relevance_score:
                    contexts.append(
                        RAGContext(
                            source_id=result.id,
                            source_type=result.metadata.get("type", "document"),
                            title=result.metadata.get("title", "Unknown"),
                            content=result.metadata.get("abstract", ""),
                            relevance_score=result.score,
                            metadata=result.metadata
                        )
                    )

        if contexts:
            contexts.sort(key=lambda c: c.relevance_score, reverse=True)
            max_contexts = self.top_k + (self.doc_top_k if self.supporting_docs_repository else 0)
            contexts = contexts[:max_contexts]

        logger.debug(f"Retrieved {len(contexts)} relevant contexts for query")
        return contexts
    
    def _format_context(self, contexts: List[RAGContext]) -> str:
        """
        Format contexts for LLM prompt.
        
        Args:
            contexts: List of context items
            
        Returns:
            Formatted context string
        """
        if not contexts:
            return "No relevant datasets found in the database."
        
        formatted = []
        for i, ctx in enumerate(contexts, 1):
            formatted.append(f"""
### Source {i}: {ctx.title}
- Relevance Score: {ctx.relevance_score:.2%}
- Type: {ctx.source_type}
- ID: {ctx.source_id}

Content:
{ctx.content[:1000]}{'...' if len(ctx.content) > 1000 else ''}
""")
        
        return "\n".join(formatted)
    
    def _format_sources_for_response(self, contexts: List[RAGContext]) -> str:
        """Format sources as citations for the response."""
        if not contexts:
            return ""
        
        sources = [
            f"[{i}] {ctx.title} (relevance: {ctx.relevance_score:.0%})"
            for i, ctx in enumerate(contexts, 1)
        ]
        return "\n\n**Sources:**\n" + "\n".join(sources)

    def _fallback_answer(self, query: str, contexts: List[RAGContext]) -> str:
        """
        Generate a deterministic fallback response when the LLM is unavailable.
        """
        if not contexts:
            return (
                "I could not generate a model response and found no relevant datasets. "
                "Please refine your query with more specific terms."
            )

        lines = [
            "The language model is unavailable. Here are relevant datasets based on semantic search:"
        ]
        for ctx in contexts[:5]:
            lines.append(f"- {ctx.title} (score: {ctx.relevance_score:.2f})")

        lines.append(
            "You can ask for details about any of these datasets or refine the query."
        )
        return "\n".join(lines)
    
    def query(self, query: str, include_sources: bool = True) -> RAGResponse:
        """
        Execute a single RAG query.
        
        Args:
            query: User question
            include_sources: Whether to include sources in response
            
        Returns:
            RAGResponse with answer and sources
        """
        import time
        start_time = time.time()
        
        # Step 1: Retrieve relevant context
        contexts = self._retrieve_context(query)
        
        # Step 2: Format context for LLM
        formatted_context = self._format_context(contexts)
        
        # Step 3: Generate answer
        try:
            answer = self.gemini_service.generate(query, context=formatted_context)
            
            # Add source citations if requested
            if include_sources and contexts:
                answer += self._format_sources_for_response(contexts)
                
        except GeminiError as e:
            logger.error(f"LLM generation failed: {e}")
            answer = self._fallback_answer(query, contexts)
        
        processing_time = (time.time() - start_time) * 1000
        
        return RAGResponse(
            answer=answer,
            sources=contexts,
            query=query,
            processing_time_ms=processing_time
        )
    
    def chat(
        self,
        message: str,
        conversation_id: Optional[str] = None,
        include_sources: bool = True
    ) -> RAGResponse:
        """
        Execute a chat turn with conversation history.
        
        Args:
            message: User message
            conversation_id: ID of existing conversation (creates new if None)
            include_sources: Whether to include sources
            
        Returns:
            RAGResponse with answer and conversation ID
        """
        import time
        start_time = time.time()
        
        # Get or create conversation
        if conversation_id and conversation_id in self.conversations:
            conversation = self.conversations[conversation_id]
        else:
            conversation = Conversation()
            self.conversations[conversation.id] = conversation
        
        # Add user message
        conversation.add_turn("user", message)
        
        # Retrieve context based on current message
        contexts = self._retrieve_context(message)
        formatted_context = self._format_context(contexts)
        
        # Get conversation history
        history = conversation.get_history(max_turns=10)
        
        # Generate response with history and context
        try:
            answer = self.gemini_service.chat(
                messages=history,
                context=formatted_context
            )
            
            # Add source citations if requested
            if include_sources and contexts:
                answer += self._format_sources_for_response(contexts)
                
        except GeminiError as e:
            logger.error(f"LLM chat failed: {e}")
            answer = self._fallback_answer(message, contexts)
        
        # Add assistant response to conversation
        conversation.add_turn("assistant", answer, contexts)
        
        processing_time = (time.time() - start_time) * 1000
        
        return RAGResponse(
            answer=answer,
            sources=contexts,
            query=message,
            processing_time_ms=processing_time,
            conversation_id=conversation.id
        )
    
    def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """Get a conversation by ID."""
        return self.conversations.get(conversation_id)
    
    def clear_conversation(self, conversation_id: str) -> bool:
        """Clear a conversation's history."""
        if conversation_id in self.conversations:
            self.conversations[conversation_id].clear()
            return True
        return False
    
    def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation."""
        if conversation_id in self.conversations:
            del self.conversations[conversation_id]
            return True
        return False
    
    def list_conversations(self) -> List[Dict]:
        """List all active conversations."""
        return [
            {
                "id": conv.id,
                "turns": len(conv.turns),
                "created_at": conv.created_at.isoformat(),
                "updated_at": conv.updated_at.isoformat()
            }
            for conv in self.conversations.values()
        ]
