"""External vendor integration adapters."""
from app.integrations.gemini_client import GeminiClient
from app.integrations.serpapi_client import SerpApiClient

__all__ = ["GeminiClient", "SerpApiClient"]
