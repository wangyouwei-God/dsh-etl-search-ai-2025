"""
Application: Document Processor Interface and Implementations

This module provides document processing capabilities for RAG,
including PDF extraction, text processing, and document chunking.

Author: University of Manchester RSE Team
"""

import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


@dataclass
class DocumentChunk:
    """A chunk of document content for embedding."""
    id: str
    document_id: str
    document_title: str
    content: str
    chunk_index: int
    start_char: int
    end_char: int
    metadata: dict = field(default_factory=dict)
    
    def __len__(self) -> int:
        return len(self.content)


@dataclass
class ProcessedDocument:
    """Result of document processing."""
    id: str
    title: str
    source_path: str
    total_chars: int
    chunks: List[DocumentChunk]
    processing_error: Optional[str] = None
    
    @property
    def is_successful(self) -> bool:
        return self.processing_error is None


class IDocumentProcessor(ABC):
    """Interface for document processors."""
    
    @abstractmethod
    def can_process(self, file_path: str) -> bool:
        """Check if this processor can handle the file."""
        pass
    
    @abstractmethod
    def extract_text(self, file_path: str) -> str:
        """Extract text content from the document."""
        pass
    
    @abstractmethod
    def process(self, file_path: str, title: str = None) -> ProcessedDocument:
        """Process document and return chunks."""
        pass


class TextChunker:
    """
    Text chunking utility for RAG.
    
    Splits text into chunks with configurable overlap for better
    context preservation during retrieval.
    """
    
    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        min_chunk_size: int = 100
    ):
        """
        Initialize chunker.
        
        Args:
            chunk_size: Target size of each chunk in characters
            chunk_overlap: Overlap between consecutive chunks
            min_chunk_size: Minimum chunk size (smaller chunks are merged)
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
    
    def _clean_text(self, text: str) -> str:
        """Clean text by normalizing whitespace."""
        # Replace multiple whitespace with single space
        text = re.sub(r'\s+', ' ', text)
        # Remove leading/trailing whitespace
        text = text.strip()
        return text
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        # Simple sentence splitting (could be improved with NLP)
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def chunk(
        self,
        text: str,
        document_id: str,
        document_title: str
    ) -> List[DocumentChunk]:
        """
        Split text into chunks.
        
        Args:
            text: Full document text
            document_id: Document identifier
            document_title: Document title for metadata
            
        Returns:
            List of DocumentChunk objects
        """
        text = self._clean_text(text)
        
        if len(text) < self.min_chunk_size:
            # Document too small, return as single chunk
            return [DocumentChunk(
                id=f"{document_id}_chunk_0",
                document_id=document_id,
                document_title=document_title,
                content=text,
                chunk_index=0,
                start_char=0,
                end_char=len(text)
            )]
        
        chunks = []
        sentences = self._split_into_sentences(text)
        
        current_chunk = ""
        current_start = 0
        chunk_index = 0
        char_position = 0
        
        for sentence in sentences:
            potential_chunk = current_chunk + " " + sentence if current_chunk else sentence
            
            if len(potential_chunk) > self.chunk_size and current_chunk:
                # Current chunk is full, save it
                chunks.append(DocumentChunk(
                    id=f"{document_id}_chunk_{chunk_index}",
                    document_id=document_id,
                    document_title=document_title,
                    content=current_chunk.strip(),
                    chunk_index=chunk_index,
                    start_char=current_start,
                    end_char=char_position
                ))
                
                chunk_index += 1
                
                # Start new chunk with overlap
                overlap_text = current_chunk[-self.chunk_overlap:] if len(current_chunk) > self.chunk_overlap else ""
                current_chunk = overlap_text + " " + sentence
                current_start = char_position - len(overlap_text)
            else:
                current_chunk = potential_chunk
            
            char_position += len(sentence) + 1  # +1 for space
        
        # Add final chunk
        if current_chunk and len(current_chunk.strip()) >= self.min_chunk_size:
            chunks.append(DocumentChunk(
                id=f"{document_id}_chunk_{chunk_index}",
                document_id=document_id,
                document_title=document_title,
                content=current_chunk.strip(),
                chunk_index=chunk_index,
                start_char=current_start,
                end_char=len(text)
            ))
        
        logger.debug(f"Created {len(chunks)} chunks from {len(text)} chars")
        return chunks


class TextFileProcessor(IDocumentProcessor):
    """Processor for plain text files."""
    
    SUPPORTED_EXTENSIONS = {'.txt', '.md', '.rst', '.csv'}
    
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        self.chunker = TextChunker(chunk_size, chunk_overlap)
    
    def can_process(self, file_path: str) -> bool:
        ext = Path(file_path).suffix.lower()
        return ext in self.SUPPORTED_EXTENSIONS
    
    def extract_text(self, file_path: str) -> str:
        """Extract text from file."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Failed to read {file_path}: {e}")
            raise
    
    def process(self, file_path: str, title: str = None) -> ProcessedDocument:
        """Process text file into chunks."""
        doc_id = str(uuid4())
        doc_title = title or Path(file_path).name
        
        try:
            text = self.extract_text(file_path)
            chunks = self.chunker.chunk(text, doc_id, doc_title)
            
            return ProcessedDocument(
                id=doc_id,
                title=doc_title,
                source_path=file_path,
                total_chars=len(text),
                chunks=chunks
            )
        except Exception as e:
            return ProcessedDocument(
                id=doc_id,
                title=doc_title,
                source_path=file_path,
                total_chars=0,
                chunks=[],
                processing_error=str(e)
            )


class PDFProcessor(IDocumentProcessor):
    """Processor for PDF files using PyMuPDF (optional dependency)."""
    
    SUPPORTED_EXTENSIONS = {'.pdf'}
    
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        self.chunker = TextChunker(chunk_size, chunk_overlap)
        self._pymupdf_available = self._check_pymupdf()
    
    def _check_pymupdf(self) -> bool:
        """Check if PyMuPDF is available."""
        try:
            import fitz  # PyMuPDF
            return True
        except ImportError:
            logger.warning("PyMuPDF not installed. PDF processing will be limited.")
            return False
    
    def can_process(self, file_path: str) -> bool:
        ext = Path(file_path).suffix.lower()
        return ext in self.SUPPORTED_EXTENSIONS and self._pymupdf_available
    
    def extract_text(self, file_path: str) -> str:
        """Extract text from PDF using PyMuPDF."""
        if not self._pymupdf_available:
            raise RuntimeError("PyMuPDF not available for PDF processing")
        
        import fitz  # PyMuPDF
        
        text_parts = []
        try:
            with fitz.open(file_path) as doc:
                for page in doc:
                    text_parts.append(page.get_text())
            
            return "\n".join(text_parts)
        except Exception as e:
            logger.error(f"Failed to extract PDF {file_path}: {e}")
            raise
    
    def process(self, file_path: str, title: str = None) -> ProcessedDocument:
        """Process PDF file into chunks."""
        doc_id = str(uuid4())
        doc_title = title or Path(file_path).stem
        
        try:
            text = self.extract_text(file_path)
            chunks = self.chunker.chunk(text, doc_id, doc_title)
            
            return ProcessedDocument(
                id=doc_id,
                title=doc_title,
                source_path=file_path,
                total_chars=len(text),
                chunks=chunks
            )
        except Exception as e:
            return ProcessedDocument(
                id=doc_id,
                title=doc_title,
                source_path=file_path,
                total_chars=0,
                chunks=[],
                processing_error=str(e)
            )


class DocumentProcessorFactory:
    """Factory for creating appropriate document processors."""
    
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        self.processors = [
            TextFileProcessor(chunk_size, chunk_overlap),
            PDFProcessor(chunk_size, chunk_overlap),
        ]
    
    def get_processor(self, file_path: str) -> Optional[IDocumentProcessor]:
        """Get appropriate processor for file."""
        for processor in self.processors:
            if processor.can_process(file_path):
                return processor
        return None
    
    def process(self, file_path: str, title: str = None) -> Optional[ProcessedDocument]:
        """Process file using appropriate processor."""
        processor = self.get_processor(file_path)
        if processor:
            return processor.process(file_path, title)
        return None
    
    def can_process(self, file_path: str) -> bool:
        """Check if any processor can handle the file."""
        return any(p.can_process(file_path) for p in self.processors)
