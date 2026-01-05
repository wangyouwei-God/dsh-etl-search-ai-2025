export interface BoundingBox {
  west_longitude: number;
  east_longitude: number;
  south_latitude: number;
  north_latitude: number;
}

export interface Metadata {
  title: string;
  abstract: string;
  keywords: string[];
  contact_organization?: string;
  contact_email?: string;
  dataset_language?: string;
  topic_category?: string;
  bounding_box?: BoundingBox;
  temporal_extent_start?: string;
  temporal_extent_end?: string;
  metadata_date?: string;
}

export interface Dataset {
  id: string;
  title: string;
  abstract: string;
  metadata_url: string;
  created_at: string;
  last_updated: string;
  metadata?: Metadata;
}

export interface SearchResult {
  id: string;
  title: string;
  abstract: string;
  score: number;
  keywords: string[];
  has_geo_extent: boolean;
  has_temporal_extent: boolean;
  center_lat?: number;
  center_lon?: number;
}

export interface SearchResponse {
  query: string;
  total_results: number;
  results: SearchResult[];
  processing_time_ms: number;
}

export interface HealthCheck {
  status: string;
  database_connected: boolean;
  vector_db_connected: boolean;
  total_datasets: number;
  total_vectors: number;
  embedding_model: string;
  embedding_dimension: number;
}

// Chat/RAG types
export interface ChatSource {
  id: string;
  title: string;
  source_type: string;
  relevance_score: number;
  content_preview?: string;
}

export interface ChatRequest {
  message: string;
  conversation_id?: string;
  include_sources?: boolean;
}

export interface ChatResponse {
  answer: string;
  conversation_id: string;
  sources: ChatSource[];
  processing_time_ms: number;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  sources?: ChatSource[];
}
