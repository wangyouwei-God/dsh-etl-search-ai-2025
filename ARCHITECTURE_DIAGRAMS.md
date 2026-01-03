# Backend Architecture Diagrams

## 1. Clean Architecture Layer Dependency

```
┌─────────────────────────────────────────────────────────────┐
│                      API LAYER                              │
│  FastAPI (main.py)  - REST Endpoints & Service Init        │
│  Pydantic Schemas   - Request/Response Validation           │
│  Middleware         - CORS, Error Handling                  │
└───────────────────────────┬─────────────────────────────────┘
                            │ imports from
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                  APPLICATION LAYER                          │
│  IEmbeddingService  - Text-to-vector interface             │
│  IMetadataExtractor - Multi-format extraction interface    │
│  Use Cases (TBD)    - Orchestration logic                   │
│  DTOs (TBD)         - Data transfer objects                 │
└───────────────────────────┬─────────────────────────────────┘
                            │ imports from
                            ↓
        ┌───────────────────────────────────────┐
        │   INFRASTRUCTURE LAYER                │
        │  - SQLiteDatasetRepository            │
        │  - ChromaVectorRepository             │
        │  - HuggingFaceEmbeddingService        │
        │  - JSONExtractor, XMLExtractor        │
        │  - ExtractorFactory                   │
        │  - MetadataFetcher                    │
        │  - HTTPClient                         │
        └───────────┬─────────────────┬─────────┘
                    │ imports from    │
                    ↓                 ↑
┌─────────────────────────────────────────────────────────────┐
│                    DOMAIN LAYER                             │
│  NO EXTERNAL DEPENDENCIES - PURE BUSINESS LOGIC             │
│                                                              │
│  Entities:                                                   │
│  ├─ Dataset                                                 │
│  ├─ Metadata                                                │
│  └─ BoundingBox                                             │
│                                                              │
│  Repository Interfaces:                                      │
│  ├─ IDatasetRepository                                      │
│  └─ IVectorRepository                                       │
│                                                              │
│  Exceptions:                                                │
│  ├─ RepositoryError, DatasetNotFoundError                  │
│  └─ VectorRepositoryError, VectorNotFoundError             │
└─────────────────────────────────────────────────────────────┘

DEPENDENCY FLOW VALIDATION:
✓ Domain → never imports from higher layers
✓ Application → only imports from Domain
✓ Infrastructure → imports from Domain and Application
✓ API → imports from all layers (valid)
✓ No circular dependencies
```

## 2. Dataset Ingestion Pipeline

```
┌──────────────────────────────────────────────────────────────────┐
│                      ETL PIPELINE FLOW                           │
└──────────────────────────────────────────────────────────────────┘

1. METADATA FETCHING
   ┌─────────────────────────────────────────┐
   │ scripts/etl_runner.py                   │
   │ ├─ Read dataset UUID list               │
   │ └─ Call MetadataFetcher.fetch()         │
   └──────────────────┬──────────────────────┘
                      │
                      ↓
   ┌─────────────────────────────────────────┐
   │ infrastructure/etl/fetcher.py            │
   │ MetadataFetcher                         │
   ├─ Try JSON format first (faster)        │
   ├─ Fallback to XML format                │
   ├─ Support multiple catalogues (CEH, CEDA) │
   ├─ Handle HTTP retries with exponential   │
   │  backoff                                │
   └──────────────────┬──────────────────────┘
                      │ returns (file_path, format)
                      ↓
2. METADATA EXTRACTION
   ┌─────────────────────────────────────────┐
   │ infrastructure/etl/factory/              │
   │ ExtractorFactory.create_extractor()     │
   ├─ Detect file type from extension       │
   ├─ Return JSONExtractor or XMLExtractor  │
   └──────────────────┬──────────────────────┘
                      │
                      ↓
   ┌─────────────────────────────────────────┐
   │ infrastructure/etl/extractors/           │
   │                                         │
   │ JSONExtractor.extract()                 │
   │ ├─ Parse JSON                           │
   │ ├─ Extract title, abstract (mandatory)  │
   │ ├─ Extract keywords, bbox, temporal     │
   │ └─ Return Metadata entity               │
   │                                         │
   │ XMLExtractor.extract()                  │
   │ ├─ Parse ISO 19139 XML                  │
   │ ├─ Handle namespaces (gmd, gco, gml)   │
   │ ├─ XPath-based element extraction       │
   │ └─ Return Metadata entity               │
   └──────────────────┬──────────────────────┘
                      │ returns Metadata domain entity
                      ↓
3. DATASET ENTITY CREATION
   ┌─────────────────────────────────────────┐
   │ domain/entities/dataset.py              │
   │ Dataset(                                │
   │   id=uuid4(),                           │
   │   title=metadata.title,                 │
   │   abstract=metadata.abstract,           │
   │   metadata_url=source_url,              │
   │   created_at=now(),                     │
   │   last_updated=now()                    │
   │ )                                       │
   └──────────────────┬──────────────────────┘
                      │
                      ↓
4. EMBEDDING GENERATION
   ┌─────────────────────────────────────────┐
   │ infrastructure/services/                 │
   │ embedding_service.py                    │
   │ HuggingFaceEmbeddingService             │
   ├─ Model: sentence-transformers/          │
   │  all-MiniLM-L6-v2                       │
   ├─ Input: title + " " + abstract          │
   ├─ Output: List[float] (384 dimensions)  │
   ├─ Batch processing support              │
   └──────────────────┬──────────────────────┘
                      │ returns embedding vector
                      ↓
5. PERSISTENCE LAYER
   ┌──────────────────────────────┐
   │ Database Persistence         │
   │                              │
   │ SQLiteDatasetRepository      │
   │ └─ Save Dataset + Metadata   │
   │    to SQLite with transaction│
   │    handling and conflict     │
   │    resolution               │
   └────────────┬─────────────────┘
                │
                ├──────────────────────────┐
                ↓                          ↓
   ┌─────────────────────┐  ┌──────────────────────┐
   │ SQLite Tables       │  │ ChromaDB Vector DB   │
   │                     │  │                      │
   │ datasets            │  │ Collection:          │
   │ ├─ id (PK)         │  │ dataset_embeddings   │
   │ ├─ title           │  │                      │
   │ ├─ abstract        │  │ Entry:               │
   │ ├─ metadata_url    │  │ ├─ ID: dataset UUID  │
   │ └─ timestamps      │  │ ├─ Vector: 384-dim  │
   │                     │  │ └─ Metadata:        │
   │ metadata           │  │    ├─ title         │
   │ ├─ dataset_id (FK) │  │    ├─ keywords      │
   │ ├─ title           │  │    ├─ bbox center   │
   │ ├─ abstract        │  │    └─ topic_cat     │
   │ ├─ keywords_json   │  │                      │
   │ ├─ bbox_json       │  │ Similarity Search:   │
   │ ├─ temporal_start  │  │ ├─ HNSW index       │
   │ ├─ temporal_end    │  │ ├─ Cosine similarity│
   │ ├─ contact_*       │  │ └─ Top-K retrieval  │
   │ └─ topic_category  │  │                      │
   └─────────────────────┘  └──────────────────────┘

RESULT: Dataset fully indexed and searchable
```

## 3. Semantic Search Pipeline

```
┌──────────────────────────────────────────────────────────────────┐
│                    SEMANTIC SEARCH FLOW                          │
└──────────────────────────────────────────────────────────────────┘

1. USER QUERY
   ┌────────────────────────────────────┐
   │ REST API Request                   │
   │ GET /api/search?q="land cover"     │
   │            &limit=10               │
   └──────────────────┬─────────────────┘
                      │
                      ↓
2. QUERY EMBEDDING
   ┌────────────────────────────────────┐
   │ HuggingFaceEmbeddingService        │
   ├─ generate_embedding(query_text)   │
   ├─ Same model as indexing           │
   │  (all-MiniLM-L6-v2)               │
   └──────────────────┬─────────────────┘
                      │ returns 384-dim vector
                      ↓
3. VECTOR SIMILARITY SEARCH
   ┌────────────────────────────────────┐
   │ ChromaVectorRepository.search()     │
   │                                    │
   │ Query:                             │
   │ ├─ query_vector: 384-dim           │
   │ ├─ limit: 10                       │
   │ └─ similarity_metric: cosine       │
   │                                    │
   │ Processing:                        │
   │ ├─ Use HNSW index for fast search │
   │ ├─ Compute cosine similarity       │
   │ ├─ Convert distance to score       │
   │ │  (score = 1 - distance/2)       │
   │ └─ Return top K results            │
   └──────────────────┬─────────────────┘
                      │ returns VectorSearchResult[]
                      ↓
4. RESULT ASSEMBLY
   ┌────────────────────────────────────┐
   │ For each VectorSearchResult:        │
   │ ├─ Extract ID and similarity score │
   │ ├─ Fetch dataset from SQLite       │
   │ ├─ Parse metadata (JSON fields)    │
   │ │  ├─ keywords (JSON array)        │
   │ │  ├─ bbox (JSON object)           │
   │ │  └─ temporal extent              │
   │ └─ Create SearchResultSchema       │
   └──────────────────┬─────────────────┘
                      │
                      ↓
5. REST RESPONSE
   ┌────────────────────────────────────┐
   │ SearchResponseSchema               │
   │ ├─ query: "land cover"            │
   │ ├─ total_results: 10              │
   │ ├─ processing_time_ms: 45.2       │
   │ └─ results: [                      │
   │     {                              │
   │       id: "uuid-1",                │
   │       title: "Land Cover Map 2020",│
   │       score: 0.87,                 │
   │       keywords: [...],             │
   │       bbox: {...},                 │
   │       temporal_extent: {...}       │
   │     },                             │
   │     ...                            │
   │   ]                                │
   └────────────────────────────────────┘
```

## 4. Class Hierarchy and Relationships

```
┌────────────────────────────────────────────────────────────────┐
│                     DOMAIN LAYER                               │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  @dataclass                                                   │
│  ┌──────────────────┐                                         │
│  │ BoundingBox      │                                         │
│  ├──────────────────┤                                         │
│  │ - west_lon       │                                         │
│  │ - east_lon       │                                         │
│  │ - south_lat      │                                         │
│  │ - north_lat      │                                         │
│  ├──────────────────┤                                         │
│  │ + get_center()   │                                         │
│  │ + get_area()     │                                         │
│  │ + __post_init__()│ ← Validates coordinates               │
│  └──────────────────┘                                         │
│          △                                                      │
│          │ has-a                                               │
│          │                                                     │
│  @dataclass                                                   │
│  ┌──────────────────────┐                                     │
│  │ Metadata             │                                     │
│  ├──────────────────────┤                                     │
│  │ - title (mandatory)  │                                     │
│  │ - abstract (mandatory)                                     │
│  │ - keywords: List[str]│                                     │
│  │ - bounding_box?      │                                     │
│  │ - temporal_start?    │                                     │
│  │ - temporal_end?      │                                     │
│  │ - contact_*          │                                     │
│  │ - topic_category     │                                     │
│  ├──────────────────────┤                                     │
│  │ + is_geospatial()    │                                     │
│  │ + has_temporal()     │                                     │
│  │ + add_keywords()     │                                     │
│  │ + __post_init__()    │                                     │
│  └──────────────────────┘                                     │
│          △                                                      │
│          │ has-a                                               │
│          │                                                     │
│  @dataclass                                                   │
│  ┌──────────────────────┐                                     │
│  │ Dataset              │                                     │
│  ├──────────────────────┤                                     │
│  │ - id: UUID           │                                     │
│  │ - title              │                                     │
│  │ - abstract           │                                     │
│  │ - metadata_url       │                                     │
│  │ - created_at         │                                     │
│  │ - last_updated       │                                     │
│  ├──────────────────────┤                                     │
│  │ + is_complete()      │                                     │
│  │ + update_metadata()  │                                     │
│  └──────────────────────┘                                     │
│          △                                                      │
│          │ persisted-by                                        │
│          │                                                     │
│  ┌────────────────────────┐                                   │
│  │ <<interface>>          │                                   │
│  │ IDatasetRepository     │                                   │
│  ├────────────────────────┤                                   │
│  │ + save()               │                                   │
│  │ + get_by_id()          │                                   │
│  │ + get_all()            │                                   │
│  │ + search_by_title()    │                                   │
│  │ + delete()             │                                   │
│  │ + count()              │                                   │
│  └────────────────────────┘                                   │
│          △                                                      │
│          │ implements                                          │
│          │                                                     │
│  @dataclass                                                   │
│  ┌────────────────────────────────────┐                       │
│  │ VectorSearchResult                 │                       │
│  ├────────────────────────────────────┤                       │
│  │ - id: str                          │                       │
│  │ - score: float                     │                       │
│  │ - metadata: Dict[str, Any]         │                       │
│  │ - distance?: float                 │                       │
│  └────────────────────────────────────┘                       │
│          △                                                      │
│          │ returned-by                                         │
│          │                                                     │
│  ┌────────────────────────────────────┐                       │
│  │ <<interface>>                      │                       │
│  │ IVectorRepository                  │                       │
│  ├────────────────────────────────────┤                       │
│  │ + upsert_vector()                  │                       │
│  │ + upsert_vectors_batch()           │                       │
│  │ + search()                         │                       │
│  │ + get_by_id()                      │                       │
│  │ + delete()                         │                       │
│  │ + count()                          │                       │
│  │ + clear()                          │                       │
│  └────────────────────────────────────┘                       │
│                                                                │
└────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────┐
│                  INFRASTRUCTURE LAYER                          │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  ┌────────────────────────────┐                               │
│  │ SQLiteDatasetRepository    │                               │
│  │ <<implements>>             │                               │
│  │ IDatasetRepository         │                               │
│  ├────────────────────────────┤                               │
│  │ - session: SQLAlchemy      │                               │
│  ├────────────────────────────┤                               │
│  │ + save(Dataset, Metadata)  │                               │
│  │ + get_by_id(id)            │                               │
│  │ + ...                      │                               │
│  └────────────────────────────┘                               │
│          △                                                      │
│          │ uses                                                │
│          │                                                     │
│  ┌────────────────────────────┐                               │
│  │ DatasetModel (SQLAlchemy)  │                               │
│  ├────────────────────────────┤                               │
│  │ - id: VARCHAR (PK)         │                               │
│  │ - title: VARCHAR           │                               │
│  │ - abstract: TEXT           │                               │
│  │ - metadata_url: VARCHAR    │                               │
│  │ - timestamps               │                               │
│  └────────────────────────────┘                               │
│          △                                                      │
│          │ one-to-one                                          │
│          │                                                     │
│  ┌────────────────────────────────┐                           │
│  │ MetadataModel (SQLAlchemy)     │                           │
│  ├────────────────────────────────┤                           │
│  │ - id: INTEGER (PK)             │                           │
│  │ - dataset_id: VARCHAR (FK)     │                           │
│  │ - title, abstract              │                           │
│  │ - keywords_json: TEXT          │                           │
│  │ - bounding_box_json: TEXT      │                           │
│  │ - temporal_extent              │                           │
│  │ - contact_*, metadata_date     │                           │
│  ├────────────────────────────────┤                           │
│  │ + get_keywords(): List[str]    │                           │
│  │ + set_keywords(keywords)       │                           │
│  │ + get_bounding_box(): Dict     │                           │
│  │ + set_bounding_box(bbox)       │                           │
│  └────────────────────────────────┘                           │
│                                                                │
│  ┌─────────────────────────────┐                              │
│  │ ChromaVectorRepository      │                              │
│  │ <<implements>>              │                              │
│  │ IVectorRepository           │                              │
│  ├─────────────────────────────┤                              │
│  │ - client: chromadb.Client   │                              │
│  │ - collection: Collection    │                              │
│  ├─────────────────────────────┤                              │
│  │ + search(query_vec) → [...]  │                             │
│  │ + upsert_vector()            │                             │
│  └─────────────────────────────┘                              │
│                                                                │
│  ┌──────────────────────────────┐                             │
│  │ HuggingFaceEmbeddingService  │                             │
│  │ <<implements>>               │                             │
│  │ IEmbeddingService            │                             │
│  ├──────────────────────────────┤                             │
│  │ - model: SentenceTransformer │                             │
│  │ - dimension: 384             │                             │
│  ├──────────────────────────────┤                             │
│  │ + generate_embedding(text)   │                             │
│  │ + generate_embeddings_batch()│                             │
│  │ + get_dimension()            │                             │
│  │ + compute_similarity()       │                             │
│  └──────────────────────────────┘                             │
│                                                                │
│  ┌─────────────────────────────┐                              │
│  │ <<interface>>               │                              │
│  │ IMetadataExtractor          │                              │
│  ├─────────────────────────────┤                              │
│  │ + extract() → Metadata      │                              │
│  │ + can_extract() → bool      │                              │
│  └─────────────────────────────┘                              │
│    △ △                                                        │
│    │ │ implemented-by                                         │
│    │ │                                                        │
│    │ ├─────────────────────────┐                              │
│    │                           │                              │
│    │ ┌──────────────────────┐  ┌──────────────────────────┐  │
│    │ │ JSONExtractor       │  │ XMLExtractor (ISO 19139) │  │
│    │ ├──────────────────────┤  ├──────────────────────────┤  │
│    │ │ + extract()          │  │ + extract()               │  │
│    │ │ + can_extract()      │  │ + can_extract()           │  │
│    │ │ + _transform_to_meta │  │ + _transform_to_meta      │  │
│    │ │   data()             │  │   data()                  │  │
│    │ └──────────────────────┘  │ + XPath-based queries    │  │
│    │                           │ + Namespace handling      │  │
│    │                           └──────────────────────────┘  │
│    │                                                         │
│    └───────────────┬──────────────────────────────────────────┘
│                    │ created-by
│                    │
│    ┌───────────────────────────────┐
│    │ ExtractorFactory              │
│    ├───────────────────────────────┤
│    │ - _extractors: Dict           │
│    │ - _extension_map: Dict        │
│    ├───────────────────────────────┤
│    │ + create_extractor()          │
│    │ + create_extractor_by_format()│
│    │ + register_extractor()        │
│    │ + get_supported_formats()     │
│    └───────────────────────────────┘
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

## 5. API Endpoints Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                    FastAPI Application                         │
│                      (api/main.py)                             │
└────────────────────────────────────────────────────────────────┘

┌─────────────────┐
│ Lifespan Setup  │
│ ├─ Get DB       │──→ DatabaseConnection
│ ├─ Init Embed   │──→ HuggingFaceEmbeddingService
│ └─ Init Vector  │──→ ChromaVectorRepository
└────────┬────────┘
         │
         ↓
┌────────────────────────────────────────────────────────────────┐
│                    API Routes                                  │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  GET /
│  └─ root()
│     └─ returns: {"name": "...", "endpoints": {...}}
│
│  GET /health
│  └─ health_check()
│     ├─ Query: SELECT COUNT(*) FROM datasets
│     ├─ Query: vector_repo.count()
│     └─ returns: HealthCheckSchema
│        ├─ status: "healthy"
│        ├─ database_connected: bool
│        ├─ vector_db_connected: bool
│        ├─ total_datasets: int
│        ├─ total_vectors: int
│        ├─ embedding_model: str
│        └─ embedding_dimension: int
│
│  GET /api/search?q=<query>&limit=<n>
│  └─ search_datasets(q: str, limit: int)
│     ├─ embedding_service.generate_embedding(q)
│     ├─ vector_repository.search(embedding, limit)
│     ├─ for each result:
│     │  ├─ Parse metadata (keywords, bbox)
│     │  └─ Create SearchResultSchema
│     └─ returns: SearchResponseSchema
│        ├─ query: str
│        ├─ total_results: int
│        ├─ processing_time_ms: float
│        └─ results: List[SearchResultSchema]
│
│  GET /api/datasets/<dataset_id>
│  └─ get_dataset(dataset_id: str)
│     ├─ repository.get_by_id(dataset_id)
│     ├─ Convert entities to schemas
│     └─ returns: DatasetSchema
│        ├─ id: UUID
│        ├─ title: str
│        ├─ abstract: str
│        ├─ metadata: MetadataSchema
│        └─ timestamps
│
│  GET /api/datasets?limit=<n>&offset=<offset>
│  └─ list_datasets(limit: int, offset: int)
│     ├─ repository.get_all(limit, offset)
│     └─ returns: List[DatasetSchema]
│
└────────────────────────────────────────────────────────────────┘

Pydantic Schemas (api/models.py):
├─ DatasetSchema
│  ├─ id: str
│  ├─ title: str
│  ├─ abstract: str
│  ├─ metadata: MetadataSchema
│  └─ timestamps
├─ SearchResultSchema
│  ├─ id: str
│  ├─ title: str
│  ├─ score: float
│  ├─ keywords: List[str]
│  └─ bbox info
├─ SearchResponseSchema
│  ├─ query: str
│  ├─ results: List[SearchResultSchema]
│  └─ processing_time_ms: float
├─ MetadataSchema
│  ├─ title, abstract
│  ├─ keywords, topic_category
│  ├─ bounding_box: BoundingBoxSchema
│  └─ temporal info
└─ HealthCheckSchema
   ├─ status, connected flags
   ├─ counts
   └─ service info
```

## 6. Error Handling Hierarchy

```
Exception
├─ Domain Exceptions (domain/exceptions/)
│  ├─ RepositoryError
│  │  ├─ DatasetNotFoundError
│  │  └─ DatasetAlreadyExistsError
│  └─ VectorRepositoryError
│     ├─ VectorNotFoundError
│     └─ VectorDimensionError
│
├─ Application Exceptions (application/interfaces/)
│  ├─ EmbeddingError
│  │  ├─ ModelLoadError
│  │  └─ TextEmbeddingError
│  └─ ExtractorError
│     ├─ UnsupportedFormatError
│     └─ MetadataExtractionError
│
├─ Infrastructure Exceptions
│  ├─ HTTPClientError
│  │  └─ DownloadError
│  └─ FetchError
│
└─ FastAPI HTTPException (automatic error responses)
   ├─ 400 Bad Request
   ├─ 404 Not Found
   └─ 500 Internal Server Error
```

---

Generated: January 3, 2026
