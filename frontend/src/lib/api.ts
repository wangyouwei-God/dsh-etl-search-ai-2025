import type { SearchResponse, Dataset, HealthCheck } from "./types";

const API_BASE_URL = "http://localhost:8000";

export class APIError extends Error {
  constructor(
    message: string,
    public status?: number,
  ) {
    super(message);
    this.name = "APIError";
  }
}

async function fetchAPI<T>(endpoint: string): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;

  try {
    const response = await fetch(url);

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new APIError(
        errorData.detail || `HTTP error! status: ${response.status}`,
        response.status,
      );
    }

    return await response.json();
  } catch (error) {
    if (error instanceof APIError) {
      throw error;
    }
    throw new APIError(
      `Network error: ${error instanceof Error ? error.message : "Unknown error"}`,
    );
  }
}

export async function searchDatasets(
  query: string,
  limit = 10,
): Promise<SearchResponse> {
  const params = new URLSearchParams({
    q: query,
    limit: limit.toString(),
  });

  return fetchAPI<SearchResponse>(`/api/search?${params}`);
}

export async function getDataset(id: string): Promise<Dataset> {
  return fetchAPI<Dataset>(`/api/datasets/${id}`);
}

export async function getHealth(): Promise<HealthCheck> {
  return fetchAPI<HealthCheck>("/health");
}

export async function listDatasets(limit = 10, offset = 0): Promise<Dataset[]> {
  const params = new URLSearchParams({
    limit: limit.toString(),
    offset: offset.toString(),
  });

  return fetchAPI<Dataset[]>(`/api/datasets?${params}`);
}

// Chat/RAG API
export async function sendChatMessage(
  message: string,
  conversationId?: string,
  includeSources = true,
): Promise<import("./types").ChatResponse> {
  const url = `${API_BASE_URL}/api/chat`;

  try {
    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        message,
        conversation_id: conversationId,
        include_sources: includeSources,
      }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new APIError(
        errorData.detail || `HTTP error! status: ${response.status}`,
        response.status,
      );
    }

    return await response.json();
  } catch (error) {
    if (error instanceof APIError) {
      throw error;
    }
    throw new APIError(
      `Network error: ${error instanceof Error ? error.message : "Unknown error"}`,
    );
  }
}
