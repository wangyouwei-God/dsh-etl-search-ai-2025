"""
API Router: Documents

Endpoints for supporting document processing, including:
- Fetching supporting documents for a dataset
- Processing documents for RAG embeddings
- Extracting dataset ZIP files

Author: University of Manchester RSE Team
"""

import logging
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/documents", tags=["Documents"])


# ============================================================================
# Request/Response Models
# ============================================================================

class SupportingDocumentResponse(BaseModel):
    """Response model for a supporting document."""
    id: str
    dataset_id: str
    title: str
    document_type: str
    url: str
    filename: str
    is_downloaded: bool
    file_size: int


class DiscoverDocumentsResponse(BaseModel):
    """Response model for document discovery."""
    dataset_id: str
    total_documents: int
    documents: List[SupportingDocumentResponse]


class ProcessDocumentsRequest(BaseModel):
    """Request model for processing documents."""
    dataset_id: str
    max_documents: int = 5


class ProcessDocumentsResponse(BaseModel):
    """Response model for document processing."""
    dataset_id: str
    documents_processed: int
    chunks_created: int
    status: str


class ZipExtractionRequest(BaseModel):
    """Request model for ZIP extraction."""
    dataset_id: str
    download_url: Optional[str] = None


class ZipExtractionResponse(BaseModel):
    """Response model for ZIP extraction."""
    dataset_id: str
    total_files: int
    total_size_bytes: int
    files: List[dict]
    status: str


# ============================================================================
# Endpoints
# ============================================================================

@router.get(
    "/discover/{dataset_id}",
    response_model=DiscoverDocumentsResponse,
    summary="Discover supporting documents",
    description="Find all supporting documents (PDFs, reports) for a dataset"
)
async def discover_documents(dataset_id: str):
    """
    Discover supporting documents for a dataset.
    
    This endpoint queries the CEH Catalogue landing page for a dataset
    and returns a list of available supporting documents.
    """
    try:
        from infrastructure.etl.supporting_doc_fetcher import SupportingDocFetcher
        
        fetcher = SupportingDocFetcher()
        try:
            docs = fetcher.discover_documents(dataset_id)
            
            return DiscoverDocumentsResponse(
                dataset_id=dataset_id,
                total_documents=len(docs),
                documents=[
                    SupportingDocumentResponse(
                        id=doc.id,
                        dataset_id=doc.dataset_id,
                        title=doc.title,
                        document_type=doc.document_type,
                        url=doc.url,
                        filename=doc.filename,
                        is_downloaded=doc.is_downloaded,
                        file_size=doc.file_size
                    )
                    for doc in docs
                ]
            )
        finally:
            fetcher.close()
            
    except Exception as e:
        logger.error(f"Document discovery failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/process",
    response_model=ProcessDocumentsResponse,
    summary="Process documents for RAG",
    description="Download supporting documents and create vector embeddings for RAG"
)
async def process_documents(request: ProcessDocumentsRequest, background_tasks: BackgroundTasks):
    """
    Process supporting documents for a dataset.
    
    This endpoint:
    1. Discovers supporting documents for the dataset
    2. Downloads available PDFs and text files
    3. Extracts text content
    4. Creates vector embeddings for RAG search
    """
    try:
        from infrastructure.etl.supporting_doc_fetcher import SupportingDocFetcher
        from infrastructure.persistence.vector.chroma_repository import ChromaVectorRepository
        from infrastructure.services.embedding_service import HuggingFaceEmbeddingService
        from application.services.document_embedding_service import DocumentEmbeddingService
        
        # Initialize services
        embedding_service = HuggingFaceEmbeddingService()
        vector_repository = ChromaVectorRepository(
            collection_name="supporting_docs",
            persist_directory="chroma_db"
        )
        doc_embedding_service = DocumentEmbeddingService(
            embedding_service=embedding_service,
            vector_repository=vector_repository
        )
        fetcher = SupportingDocFetcher(download_dir="supporting_docs")
        
        try:
            # Fetch documents
            downloaded_docs = fetcher.fetch_all_documents(
                dataset_id=request.dataset_id,
                max_docs=request.max_documents
            )
            
            # Process each document
            total_chunks = 0
            for doc in downloaded_docs:
                if doc.file_path:
                    chunks = doc_embedding_service.process_document(
                        file_path=doc.file_path,
                        dataset_id=request.dataset_id,
                        document_type=doc.document_type
                    )
                    total_chunks += len(chunks)
            
            return ProcessDocumentsResponse(
                dataset_id=request.dataset_id,
                documents_processed=len(downloaded_docs),
                chunks_created=total_chunks,
                status="completed"
            )
            
        finally:
            fetcher.close()
            
    except Exception as e:
        logger.error(f"Document processing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/extract-zip",
    response_model=ZipExtractionResponse,
    summary="Extract dataset ZIP file",
    description="Download and extract a dataset's ZIP archive"
)
async def extract_zip(request: ZipExtractionRequest):
    """
    Extract a dataset's ZIP archive.
    
    This endpoint downloads the dataset ZIP file from CEH Catalogue
    and extracts its contents to local storage.
    """
    try:
        from infrastructure.etl.zip_extractor import ZipExtractor, ZipDownloadError
        
        extractor = ZipExtractor(
            extract_dir="extracted_datasets",
            timeout=300,
            max_size_mb=500
        )
        
        try:
            # Construct download URL if not provided
            download_url = request.download_url
            if not download_url:
                # First, try to get download_url from database
                try:
                    from infrastructure.persistence.sqlite.connection import get_database
                    from infrastructure.persistence.sqlite.models import MetadataModel
                    from pathlib import Path
                    
                    backend_dir = Path(__file__).parent.parent.parent.parent
                    db_path = str(backend_dir / "datasets.db")
                    db = get_database(db_path)
                    
                    with db.session_scope() as session:
                        metadata = session.query(MetadataModel).filter_by(
                            dataset_id=request.dataset_id
                        ).first()
                        if metadata and metadata.download_url:
                            download_url = metadata.download_url
                            logger.info(f"Using download_url from database: {download_url}")
                except Exception as e:
                    logger.warning(f"Failed to query database for download_url: {e}")
                
                # Fallback to default URL pattern if not found in database
                if not download_url:
                    # Use data-package pattern (more common for CEH datasets)
                    download_url = f"https://data-package.ceh.ac.uk/data/{request.dataset_id}.zip"
                    logger.info(f"Using fallback download_url: {download_url}")
            
            # Check if already extracted
            manifest = extractor.get_manifest(request.dataset_id)
            if manifest:
                return ZipExtractionResponse(
                    dataset_id=request.dataset_id,
                    total_files=len(manifest),
                    total_size_bytes=sum(f.file_size for f in manifest),
                    files=[
                        {
                            "filename": f.filename,
                            "format": f.file_format,
                            "size": f.file_size
                        }
                        for f in manifest[:20]  # Limit to first 20 files
                    ],
                    status="already_extracted"
                )
            
            # Download and extract
            result = extractor.extract_from_url(
                url=download_url,
                dataset_id=request.dataset_id
            )
            
            return ZipExtractionResponse(
                dataset_id=request.dataset_id,
                total_files=result.total_files,
                total_size_bytes=result.total_size,
                files=[
                    {
                        "filename": f.filename,
                        "format": f.file_format,
                        "size": f.file_size
                    }
                    for f in result.extracted_files[:20]
                ],
                status="extracted"
            )
            
        except ZipDownloadError as e:
            raise HTTPException(status_code=400, detail=f"Download failed: {e}")
        finally:
            extractor.close()
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"ZIP extraction failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/files/{dataset_id}",
    summary="List extracted files",
    description="List files extracted from a dataset's ZIP archive"
)
async def list_extracted_files(dataset_id: str):
    """
    List files extracted from a dataset's ZIP archive.
    """
    try:
        from infrastructure.etl.zip_extractor import ZipExtractor
        
        extractor = ZipExtractor(extract_dir="extracted_datasets")
        
        try:
            manifest = extractor.get_manifest(dataset_id)
            
            if not manifest:
                raise HTTPException(
                    status_code=404,
                    detail=f"No extracted files found for dataset {dataset_id}"
                )
            
            return {
                "dataset_id": dataset_id,
                "total_files": len(manifest),
                "files": [
                    {
                        "filename": f.filename,
                        "format": f.file_format,
                        "size": f.file_size,
                        "path": f.file_path
                    }
                    for f in manifest
                ]
            }
            
        finally:
            extractor.close()
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list files: {e}")
        raise HTTPException(status_code=500, detail=str(e))
