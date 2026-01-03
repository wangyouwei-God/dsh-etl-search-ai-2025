"""
Infrastructure: Gemini API Service

This module provides integration with Google's Gemini API for LLM capabilities,
supporting RAG (Retrieval Augmented Generation) and conversational features.

Author: University of Manchester RSE Team
"""

import json
import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional, Generator
import requests

logger = logging.getLogger(__name__)


class GeminiError(Exception):
    """Base exception for Gemini API errors."""
    pass


class GeminiAPIError(GeminiError):
    """Raised when API call fails."""
    def __init__(self, message: str, status_code: Optional[int] = None):
        self.status_code = status_code
        super().__init__(message)


class GeminiRateLimitError(GeminiError):
    """Raised when rate limit is exceeded."""
    pass


@dataclass
class GeminiMessage:
    """Represents a message in a conversation."""
    role: str  # 'user' or 'model'
    content: str


@dataclass
class GeminiResponse:
    """Response from Gemini API."""
    text: str
    finish_reason: str
    usage: Dict[str, int]


class IGeminiService(ABC):
    """Interface for Gemini LLM service."""
    
    @abstractmethod
    def generate(self, prompt: str, context: Optional[str] = None) -> str:
        """Generate a response for a single prompt."""
        pass
    
    @abstractmethod
    def chat(self, messages: List[GeminiMessage], context: Optional[str] = None) -> str:
        """Generate a response for a conversation."""
        pass


class GeminiService(IGeminiService):
    """
    Gemini API service using HTTP REST calls.
    
    This service provides:
    - Single-turn generation
    - Multi-turn conversation
    - RAG context injection
    - Error handling with retries
    
    Design Pattern: Adapter Pattern
    - Adapts Gemini REST API to application interface
    """
    
    BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gemini-flash-latest",
        temperature: float = 0.7,
        max_tokens: int = 2048,
        timeout: int = 60
    ):
        """
        Initialize Gemini service.
        
        Args:
            api_key: Gemini API key (defaults to GEMINI_API_KEY env var)
            model: Model name (default: gemini-flash-latest)
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum output tokens
            timeout: Request timeout in seconds
        """
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise GeminiError("GEMINI_API_KEY not provided")
        
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        
        self.session = requests.Session()
        
        logger.info(f"GeminiService initialized: model={model}, temp={temperature}")
    
    def _build_url(self, action: str = "generateContent") -> str:
        """Build the API URL."""
        return f"{self.BASE_URL}/{self.model}:{action}?key={self.api_key}"
    
    def _build_request_body(
        self,
        contents: List[Dict],
        system_instruction: Optional[str] = None
    ) -> Dict:
        """Build the request body for the API."""
        body = {
            "contents": contents,
            "generationConfig": {
                "temperature": self.temperature,
                "maxOutputTokens": self.max_tokens,
                "topP": 0.95,
                "topK": 40
            }
        }
        
        if system_instruction:
            body["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }
        
        return body
    
    def _parse_response(self, response_data: Dict) -> GeminiResponse:
        """Parse the API response."""
        try:
            candidates = response_data.get("candidates", [])
            if not candidates:
                raise GeminiAPIError("No candidates in response")
            
            candidate = candidates[0]
            content = candidate.get("content", {})
            parts = content.get("parts", [])
            
            text = ""
            for part in parts:
                if "text" in part:
                    text += part["text"]
            
            finish_reason = candidate.get("finishReason", "UNKNOWN")
            
            usage = response_data.get("usageMetadata", {})
            
            return GeminiResponse(
                text=text,
                finish_reason=finish_reason,
                usage={
                    "prompt_tokens": usage.get("promptTokenCount", 0),
                    "completion_tokens": usage.get("candidatesTokenCount", 0),
                    "total_tokens": usage.get("totalTokenCount", 0)
                }
            )
        except (KeyError, IndexError) as e:
            raise GeminiAPIError(f"Failed to parse response: {e}")
    
    def _make_request(self, body: Dict) -> GeminiResponse:
        """Make the API request with error handling."""
        url = self._build_url()
        
        try:
            response = self.session.post(
                url,
                json=body,
                headers={"Content-Type": "application/json"},
                timeout=self.timeout
            )
            
            if response.status_code == 429:
                raise GeminiRateLimitError("Rate limit exceeded")
            
            if response.status_code != 200:
                error_msg = response.text[:500]
                raise GeminiAPIError(f"API error: {error_msg}", response.status_code)
            
            return self._parse_response(response.json())
            
        except requests.exceptions.Timeout:
            raise GeminiAPIError(f"Request timed out after {self.timeout}s")
        except requests.exceptions.RequestException as e:
            raise GeminiAPIError(f"Request failed: {str(e)}")
    
    def generate(self, prompt: str, context: Optional[str] = None) -> str:
        """
        Generate a response for a single prompt.
        
        Args:
            prompt: User prompt
            context: Optional context to include (for RAG)
            
        Returns:
            Generated text response
        """
        # Build content with optional context
        if context:
            full_prompt = f"""Based on the following context, answer the user's question.

Context:
{context}

User Question: {prompt}

Please provide a helpful and accurate response based on the context provided. If the context doesn't contain relevant information, say so."""
        else:
            full_prompt = prompt
        
        contents = [
            {
                "role": "user",
                "parts": [{"text": full_prompt}]
            }
        ]
        
        body = self._build_request_body(contents)
        response = self._make_request(body)
        
        logger.debug(f"Generated response: {len(response.text)} chars, {response.usage}")
        
        return response.text
    
    def chat(
        self,
        messages: List[GeminiMessage],
        context: Optional[str] = None,
        system_prompt: Optional[str] = None
    ) -> str:
        """
        Generate a response for a multi-turn conversation.
        
        Args:
            messages: List of conversation messages
            context: Optional RAG context to include
            system_prompt: Optional system instruction
            
        Returns:
            Generated text response
        """
        # Build contents from message history
        contents = []
        
        for msg in messages:
            role = "user" if msg.role == "user" else "model"
            contents.append({
                "role": role,
                "parts": [{"text": msg.content}]
            })
        
        # Inject context into the last user message if provided
        if context and contents and contents[-1]["role"] == "user":
            original_text = contents[-1]["parts"][0]["text"]
            contents[-1]["parts"][0]["text"] = f"""Based on the following retrieved information:

{context}

{original_text}"""
        
        # Default system prompt for dataset search assistant
        if not system_prompt:
            system_prompt = """You are a helpful dataset search assistant for the University of Manchester Environmental Data Centre. Your role is to help users discover and understand environmental datasets.

When answering questions:
1. Be accurate and cite the dataset information provided
2. Explain technical terms when needed
3. Suggest related datasets if relevant
4. Be concise but thorough"""
        
        body = self._build_request_body(contents, system_instruction=system_prompt)
        response = self._make_request(body)
        
        logger.debug(f"Chat response: {len(response.text)} chars")
        
        return response.text
    
    def close(self):
        """Close the HTTP session."""
        self.session.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
