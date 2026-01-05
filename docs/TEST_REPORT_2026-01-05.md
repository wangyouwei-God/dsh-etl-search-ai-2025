# Test Report - Dataset Search and Discovery

## Scope
- Document the full feature set and current implementation status.
- Validate core ETL pipeline (metadata ingestion, persistence, embeddings).
- Validate metadata extractors (XML, JSON, JSON-LD, RDF).
- Validate repository behavior (CRUD/query methods).
- Validate API endpoints (health, search, datasets, chat/RAG, documents).
- Validate fileAccess handling (folder crawl + download).
- Run frontend static checks (type/a11y).
- Validate operational utilities (batch ETL, vector regeneration, document content indexing, Chroma sync, demo scripts).

## Test Environment
- OS: Darwin 22.6.0 (x86_64)
- Python: 3.11.13
- Node: v25.0.0
- npm: 6.14.13
- Database: SQLite (`backend/datasets.db`)
- Vector store: ChromaDB (`backend/chroma_db`)
- Embedding model: `sentence-transformers/all-MiniLM-L6-v2` (384 dims)
- LLM: Gemini (API key loaded from `.env`, not embedded in logs)

## Data Sources and Samples
- CEH Catalogue: `https://catalogue.ceh.ac.uk/id/{uuid}`
- fileAccess folder example:
  - `https://catalogue.ceh.ac.uk/datastore/eidchub/755e0369-f8db-4550-aabe-3f9c9fbcb93d`
- Supporting docs ZIP:
  - `https://data-package.ceh.ac.uk/sd/{uuid}.zip`
- UUIDs used for live ETL tests:
  - `755e0369-f8db-4550-aabe-3f9c9fbcb93d`
- UUIDs used for supporting-doc demo:
  - `be0bdc0e-bc2e-4f1d-b524-2c02798dd893`
  - `3aaa52d3-d0e1-4c10-b37e-c3d52d9c6968` (404 on docs discovery)

## Feature Inventory and Implementation Status
### Backend (ETL + Services)
- Metadata fetching from CEH Catalogue with content negotiation.
- Extractors: XML (ISO 19115), JSON (expanded), JSON-LD (Schema.org), RDF (Turtle).
- Resource abstraction (remote files, web folders, APIs) via extractor strategy.
- SQLite persistence:
  - `datasets`, `metadata`, `data_files`, `supporting_documents`, `metadata_relationships`.
  - Raw document storage (JSON/XML) + checksum.
  - Distribution fields: `download_url`, `landing_page_url`, `access_type`.
- Metadata relationships extracted from JSON and persisted in `metadata_relationships`.
- Vector embeddings:
  - Dataset embeddings from title + abstract.
  - Supporting document embeddings for RAG.
  - ChromaDB collections: `dataset_embeddings`, `supporting_docs`.
- fileAccess handling:
  - Folder crawl with depth limit and size cap.
  - Optional download for large data files.
- ZIP handling:
  - Download + extraction with nested ZIP support.
  - Manifest listing for extracted files.
- Supporting documents:
  - ZIP-first retrieval with HTML fallback.
  - DOCX/PDF/text extraction, chunking, embedding.
- Document content indexing pipeline (full-text chunks in `document_content` collection).
- RAG pipeline:
  - Retrieval from dataset and supporting docs collections.
  - Gemini response with sources and conversation memory.
- Conversation management: list, clear, delete active chat sessions.

### Operational Utilities and Demo Scripts
- Batch ETL runner for identifier lists (`metadata-file-identifiers` format).
- Vector regeneration from SQLite (rebuild ChromaDB from stored metadata).
- ChromaDB sync (removes orphaned vectors not present in SQLite).
- Document content indexing (bulk processing of supporting documents).
- Demo ZIP extraction (synthetic archive for pipeline verification).
- Demo supporting-doc RAG (discovery + vector search).
- ZIP robustness runner (`process_all_zips.py`, scale test).

## Feature-to-Code Map (Implementation Index)
### ETL and Ingestion
- Metadata fetch + retry: `backend/src/infrastructure/etl/fetcher.py`, `backend/src/infrastructure/external/http_client.py`
- Extractor factory: `backend/src/infrastructure/etl/factory/extractor_factory.py`
- XML extractor (ISO 19115): `backend/src/infrastructure/etl/extractors/xml_extractor.py`
- JSON extractor (expanded + relationships): `backend/src/infrastructure/etl/extractors/json_extractor.py`
- JSON-LD extractor (Schema.org): `backend/src/infrastructure/etl/extractors/jsonld_extractor.py`
- RDF/Turtle extractor: `backend/src/infrastructure/etl/extractors/rdf_extractor.py`
- Resource abstraction: `backend/src/domain/entities/resource.py`
- ETL orchestration: `backend/src/scripts/etl_runner.py`, `backend/src/scripts/batch_etl_runner.py`

### Data Access and File Handling
- ZIP download/extraction: `backend/src/infrastructure/etl/zip_extractor.py`
- fileAccess folder crawl + download: `backend/src/infrastructure/etl/file_access_fetcher.py`
- Supporting docs fetch (ZIP + HTML): `backend/src/infrastructure/etl/supporting_doc_fetcher.py`
- Document content extraction + chunking: `backend/src/infrastructure/etl/content_extractor.py`
- Document embedding pipeline: `backend/src/application/services/document_embedding_service.py`

### Persistence and Search
- SQLite models: `backend/src/infrastructure/persistence/sqlite/models.py`
- SQLite repository: `backend/src/infrastructure/persistence/sqlite/dataset_repository_impl.py`
- DB connection + schema migration: `backend/src/infrastructure/persistence/sqlite/connection.py`
- Embedding service: `backend/src/infrastructure/services/embedding_service.py`
- Vector store (ChromaDB): `backend/src/infrastructure/persistence/vector/chroma_repository.py`
- RAG core: `backend/src/application/services/rag_service.py`
- Gemini integration: `backend/src/infrastructure/services/gemini_service.py`

### API Surface
- Core API + search/datasets/health: `backend/src/api/main.py`
- Chat/RAG endpoints: `backend/src/api/routers/chat.py`
- Documents endpoints: `backend/src/api/routers/documents.py`

### Frontend
- Routes: `frontend/src/routes/+page.svelte`, `frontend/src/routes/chat/+page.svelte`, `frontend/src/routes/datasets/[id]/+page.svelte`
- Components: `frontend/src/lib/components/SearchBar.svelte`, `frontend/src/lib/components/DatasetCard.svelte`, `frontend/src/lib/components/DatasetDetailsSheet.svelte`, `frontend/src/lib/components/MetadataViewer.svelte`, `frontend/src/lib/components/ChatInterface.svelte`, `frontend/src/lib/components/ChatDrawer.svelte`, `frontend/src/lib/components/Header.svelte`
- Types and utilities: `frontend/src/lib/types.ts`, `frontend/src/lib/utils.ts`, `frontend/src/lib/api.ts`

### Operational Utilities
- Batch ETL runner: `backend/src/scripts/batch_etl_runner.py`
- Vector regeneration: `backend/src/scripts/regenerate_vectors.py`
- ChromaDB sync: `backend/src/scripts/sync_chromadb.py`
- Document content indexing: `backend/src/scripts/index_document_content.py`
- ZIP robustness runner: `backend/src/scripts/process_all_zips.py`
- Demo ZIP extraction: `backend/src/scripts/demo_zip_extraction.py`
- Demo supporting-doc RAG: `backend/src/scripts/demo_supporting_doc_rag.py`

### API Surface (FastAPI)
- Root:
  - `GET /` API info and endpoint list.
- Health:
  - `GET /health` service status and counts.
- Search:
  - `GET /api/search?q=...` semantic search over embeddings.
- Datasets:
  - `GET /api/datasets` list with pagination.
  - `GET /api/datasets/{id}` detail + metadata.
- Chat:
  - `POST /api/chat` RAG chat with optional sources.
  - `GET /api/chat/conversations` list conversations.
  - `DELETE /api/chat/conversations/{id}` delete.
  - `POST /api/chat/conversations/{id}/clear` clear.
- Documents:
  - `GET /api/documents/discover/{id}` list supporting docs.
  - `POST /api/documents/process` download + embed documents.
  - `POST /api/documents/extract-zip` download + extract ZIP.
  - `GET /api/documents/files/{id}` list extracted files.

### Frontend (Svelte)
- Pages:
  - Home: semantic search UI + results list.
  - Chat: RAG chat UI with sources.
  - Dataset details: metadata view and tabs.
- Components:
  - SearchBar, DatasetCard, DatasetDetailsSheet, MetadataViewer.
  - ChatInterface, ChatDrawer, Header.
- Styling:
  - Tailwind CSS + custom design system.

## Functional Coverage Matrix (All Required Features)
| Feature | Test/Command | Result |
| --- | --- | --- |
| XML/JSON/JSON-LD/RDF extractors | `python test_all_extractors.py` | PASS |
| Repository methods | `DATASETS_DB_PATH=backend/datasets.db python backend/test_repository_methods.py` | PASS |
| ETL metadata + embeddings | `python backend/src/scripts/etl_runner.py ...` | PASS |
| fileAccess crawl + download | `--download-fileaccess --fileaccess-max-files 5 --fileaccess-max-size-mb 2000` | PASS (5 files) |
| Supporting docs download + RAG chunking | ETL runner step 5.2 | PASS |
| API health/search/datasets/chat | `python - <<PY ... test_api.main()` | PASS (LLM rate limit handled with fallback response) |
| Documents API (discover/process/extract-zip/files) | TestClient script (see Section 5) | PASS |
| Frontend type/a11y checks | `npm -C frontend run check` | PASS |
| Batch ETL runner | `python backend/src/scripts/batch_etl_runner.py temp/metadata-file-identifiers-test.txt --max-datasets 1 ...` | PASS (1 dataset) |
| Demo ZIP extraction | `PYTHONPATH=backend/src python backend/src/scripts/demo_zip_extraction.py` | PASS |
| Demo supporting-doc RAG | `PYTHONPATH=backend/src python backend/src/scripts/demo_supporting_doc_rag.py` | PASS (1 dataset discovered, vector search OK) |
| Vector regeneration | `python backend/src/scripts/regenerate_vectors.py` | PASS (200/200) |
| ChromaDB sync | `python backend/src/scripts/sync_chromadb.py` | PASS (orphaned vectors removed, final count 200) |
| Document content indexing | `python backend/src/scripts/index_document_content.py` | PASS (1 doc indexed, 4 chunks) |
| ZIP robustness runner | `python backend/src/scripts/process_all_zips.py` | NOT RUN (scale test: downloads 200 ZIPs) |

## Feature-to-Test Evidence Map
| Feature Area | Evidence |
| --- | --- |
| Extractors (XML/JSON/JSON-LD/RDF) | Section 1 results; `python test_all_extractors.py` |
| Repository CRUD/query | Section 2 results; `backend/test_repository_methods.py` |
| ETL ingest + embeddings | Section 3 results; ETL runner output |
| fileAccess crawl + download | Section 3 results; 5 files downloaded |
| Supporting docs fetch + embedding | Sections 3 and 5 results |
| API health/search/datasets/chat | Section 4 results; `test_api.main()` |
| Documents API endpoints | Section 5 results; TestClient script |
| Frontend static type/a11y | Section 6 results; `npm -C frontend run check` |
| Batch ETL runner | Section 7 results; `batch_etl_runner.py` |
| ZIP extraction demo | Section 8 results; `demo_zip_extraction.py` |
| Supporting-doc RAG demo | Section 9 results; `demo_supporting_doc_rag.py` |
| Vector regeneration | Section 10 results; `regenerate_vectors.py` |
| ChromaDB sync | Section 11 results; `sync_chromadb.py` |
| Document content indexing | Section 12 results; `index_document_content.py` |
| ZIP robustness runner | Not executed (scale test) |

## Detailed Test Execution

### 1) Metadata Extractor Validation
Command:
```
python test_all_extractors.py
```
Results:
- XML Extractor: PASS
- JSON Extractor: PASS
- JSON-LD Extractor: PASS
- RDF Extractor: PASS

### 2) Repository Methods
Command:
```
DATASETS_DB_PATH=backend/datasets.db python backend/test_repository_methods.py
```
Results:
- `get_by_id`, `exists`, `search_by_title`, `count`, `get_all` all PASS
- Database count reported: 200 datasets

### 3) ETL + fileAccess Download (5 files)
Command:
```
python backend/src/scripts/etl_runner.py 755e0369-f8db-4550-aabe-3f9c9fbcb93d \
  --format json \
  --download-fileaccess \
  --fileaccess-max-files 5 \
  --fileaccess-max-depth 1 \
  --fileaccess-max-size-mb 2000 \
  --db-path backend/datasets.db \
  --vector-db-path backend/chroma_db
```
Results:
- Metadata fetched and persisted (raw JSON stored).
- fileAccess crawl discovered 5 data files.
- 5 files downloaded successfully.
- Supporting docs ZIP downloaded and extracted.
- DOCX processed into 33 chunks and embedded.
- Dataset embedding stored in ChromaDB.

Downloaded files (fileAccess):
- `extracted_datasets/755e0369-f8db-4550-aabe-3f9c9fbcb93d/avail_precip_obs_196101_196512.nc` (~1.2GB)
- `extracted_datasets/755e0369-f8db-4550-aabe-3f9c9fbcb93d/avail_precip_obs_196601_197012.nc` (~1.2GB)
- `extracted_datasets/755e0369-f8db-4550-aabe-3f9c9fbcb93d/avail_precip_obs_197101_197512.nc` (~1.3GB)
- `extracted_datasets/755e0369-f8db-4550-aabe-3f9c9fbcb93d/avail_precip_obs_197601_198012.nc` (~1.2GB)
- `extracted_datasets/755e0369-f8db-4550-aabe-3f9c9fbcb93d/avail_precip_obs_198101_198512.nc` (~1.2GB)

### 4) API + RAG Tests (Gemini Enabled)
Command (loads `.env` without echoing secrets):
```
python - <<'PY'
import os
from dotenv import load_dotenv
load_dotenv('.env')
os.environ['USE_TESTCLIENT'] = '1'
import test_api
test_api.main()
PY
```
Results:
- Health: PASS
- Semantic search: PASS (queries: river flow data, soil moisture measurements, climate change precipitation)
- Datasets list: PASS
- Chat/RAG: PASS with fallback response when Gemini is rate-limited
- Vector count reported: 200

### 5) Documents API Tests
Command (TestClient):
```
python - <<'PY'
import os
from dotenv import load_dotenv
load_dotenv('.env')
os.environ['USE_TESTCLIENT'] = '1'
from fastapi.testclient import TestClient
from backend.src.api.main import app
client = TestClient(app)
dataset_id = "755e0369-f8db-4550-aabe-3f9c9fbcb93d"
client.get(f"/api/documents/discover/{dataset_id}")
client.post("/api/documents/process", json={"dataset_id": dataset_id, "max_documents": 2})
client.post("/api/documents/extract-zip", json={
    "dataset_id": "sd-zip-test-755e",
    "download_url": f"https://data-package.ceh.ac.uk/sd/{dataset_id}.zip"
})
client.get("/api/documents/files/sd-zip-test-755e")
PY
```
Results:
- Discover: PASS (2 documents found)
- Process: PASS (1 document processed, 10 chunks created)
- Extract ZIP: PASS (3 files extracted from supporting docs ZIP)
- Files list: PASS (3 files returned)

Note: dataset ZIP URLs were not exposed in metadata; extract-zip was validated using the supporting-docs ZIP as a functional proxy.

### 6) Frontend Static Checks
Command:
```
npm -C frontend run check
```
Result:
- PASS

### 7) Batch ETL Runner (Identifier List)
Command:
```
python backend/src/scripts/batch_etl_runner.py temp/metadata-file-identifiers-test.txt \
  --max-datasets 1 \
  --db-path backend/datasets.db \
  --vector-db-path backend/chroma_db
```
Results:
- Processed 1 dataset (`755e0369-f8db-4550-aabe-3f9c9fbcb93d`) successfully.
- Metadata fetched (JSON), persisted, and embedding stored.
- fileAccess listing discovered 200 data files (download not enabled in batch mode).
- Supporting docs ZIP downloaded; 1 DOCX embedded (33 chunks).

### 8) Demo ZIP Extraction Script
Command:
```
PYTHONPATH=backend/src python backend/src/scripts/demo_zip_extraction.py
```
Results:
- Synthetic ZIP created and extracted successfully.
- 4 files extracted; manifest returned 4 entries.
- Demonstrated nested directory extraction and manifest listing.

### 9) Supporting-Document RAG Demo
Command:
```
PYTHONPATH=backend/src python backend/src/scripts/demo_supporting_doc_rag.py
```
Results:
- Supporting docs discovery succeeded for 1 dataset; 1 dataset returned 404.
- Vector search executed for 3 queries and returned ranked results.
- No new chunks processed in this run (no local PDFs/TXTs found in `supporting_docs`).

### 10) Vector Regeneration from SQLite
Command:
```
python backend/src/scripts/regenerate_vectors.py
```
Results:
- 200 datasets processed; 200 embeddings regenerated.
- Completed successfully using cached model (HF network probes logged but non-blocking).

### 11) ChromaDB Sync
Command:
```
python backend/src/scripts/sync_chromadb.py
```
Results:
- Valid dataset IDs in SQLite: 200.
- Removed 198 orphaned vectors from ChromaDB.
- Final ChromaDB count: 200.

### 12) Document Content Indexing
Command:
```
python backend/src/scripts/index_document_content.py
```
Results:
- 4 supporting documents discovered in SQLite.
- 1 DOCX indexed (4 chunks) into `document_content` collection.
- 3 supporting docs missing on disk and skipped.
- `document_content` collection count: 4 vectors.

### 13) ZIP Robustness Runner (Scale Test)
Status:
- Not executed in this run (downloads and extracts 200 ZIP datasets).

## Implementation Notes by Subsystem
### ETL Pipeline
1) Fetch metadata via `MetadataFetcher` (CEH catalogue + WAF fallback).
2) Parse via extractor factory (XML/JSON/JSON-LD/RDF).
3) Validate and normalize into domain entities.
4) Persist to SQLite with raw document + checksum.
5) Download data:
   - `download` -> ZIP extraction.
   - `fileAccess` -> directory crawl + optional download.
6) Supporting docs ZIP download + document extraction.
7) Embeddings:
   - Title/abstract -> dataset vector.
   - Document chunks -> supporting_docs vectors.

### Persistence (SQLite)
- Tables: datasets, metadata, data_files, supporting_documents, metadata_relationships.
- Raw JSON/XML stored in metadata table.
- Relationship modeling: `metadata_relationships` stores `relation`, `target`, `target_id`, `target_url`.

### Vector Store (ChromaDB)
- Collection: `dataset_embeddings`
- Collection: `supporting_docs`
- Collection: `document_content` (full-text supporting docs)
- Embedding model: sentence-transformers/all-MiniLM-L6-v2 (384 dims)

### RAG
- Retrieval from both dataset and supporting docs collections.
- Gemini-based generation with conversation memory and source citations.

### Frontend
- Search flows: query -> semantic results -> dataset details.
- Chat flows: prompt -> RAG -> sources list.
- Dataset details tabs: overview, files, metadata.

## Known Issues / Risks
1) Gemini rate limiting:
   - LLM returned "Rate limit exceeded" during tests.
   - Impact: RAG falls back to retrieval-only responses with sources.
2) Chroma telemetry:
   - Non-blocking errors: `capture() takes 1 positional argument but 3 were given`.
   - Impact: Telemetry only; core DB operations still succeed.
3) Supporting docs availability:
   - Some supporting documents are referenced in SQLite but not present on disk.
   - Impact: Document content indexing skips missing files unless they are downloaded.
4) Embedding model cache:
   - Scripts may attempt HuggingFace network checks if the model is not cached.
   - Impact: First-time runs require network access; subsequent runs are local.
5) ZIP robustness runner:
   - `process_all_zips.py` not executed in this run due to large downloads.

## Artifacts
- SQLite DB: `backend/datasets.db`
- Vector DB: `backend/chroma_db`
- Vector collections: `dataset_embeddings`, `supporting_docs`, `document_content`
- fileAccess downloads: `extracted_datasets/755e0369-f8db-4550-aabe-3f9c9fbcb93d`
- Supporting docs: `supporting_docs/755e0369-f8db-4550-aabe-3f9c9fbcb93d`

## Reproduction Notes
- Ensure `GEMINI_API_KEY` is set in `.env` before running chat tests.
- For large fileAccess datasets, adjust `--fileaccess-max-size-mb` as needed.
- Demo scripts can be run with `PYTHONPATH=backend/src` from repo root.
- Document content indexing requires supporting docs to be present on disk.
- Batch ETL requires an identifier list file (example used: `temp/metadata-file-identifiers-test.txt`).
